import os
import requests
import json
from datetime import datetime
from sqlalchemy import create_engine, text

# ==========================================
# 1. CONFIGURAÇÕES
# ==========================================
# Colocamos o subdomínio direto no código para evitar o erro de 'InvalidURL'
KOMMO_SUBDOMAIN = "miletobr" 
KOMMO_TOKEN = os.getenv("KOMMO_ACCESS_TOKEN", "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImp0aSI6IjI3YTcxNDEyMjQ3YzdkM2QyNjFmYzU1MTY1ZmQyMTFkOTJmMDJmM2NmZWVmMDBkMDFhNzQwMTM0NDBjYWM5OGE4MDBmYjI5MTYyYzc2OTgyIn0.eyJhdWQiOiI2MzM4MDNjNC0zNDVmLTQ1NDItOWY5ZS0zMDk3MTZmMjM5NjAiLCJqdGkiOiIyN2E3MTQxMjI0N2M3ZDNkMjYxZmM1NTE2NWZkMjExZDkyZjAyZjNjZmVlZjAwZDAxYTc0MDEzNDQwY2FjOThhODAwZmIyOTE2MmM3Njk4MiIsImlhdCI6MTc4NzMzNDI0MiwibmJmIjoxNzg3MzM0MjQyLCJleHAiOjE4NjE5MjAwMDAsInN1YiI6IjE0NTUyODM1IiwiZ3JhbnRfdHlwZSI6IiIsImFjY291bnRfaWQiOjM1ODU3OTgzLCJiYXNlX2RvbWFpbiI6ImtvbW1vLmNvbSIsInZlcnNpb24iOjIsInNjb3BlcyI6WyJwdXNoX25vdGlmaWNhdGlvbnMiLCJmaWxlcyIsImNybSIsImZpbGVzX2RlbGV0ZSIsIm5vdGlmaWNhdGlvbnMiXSwiaGFzaF91dWlkIjoiZWJhYWNlYWMtNjcxMC00MTgwLWEyMTMtMGJlY2Q4OGJlZmQxIiwiYXBpX2RvbWFpbiI6ImFwaS1jLmtvbW1vLmNvbSJ9.jM7d_M2nFYRAzwmuQ050KpCbCsUKtfmIkrg9B7VHiu8zG-Xh67qSBzyAZzyb1Qx2uwgS10AmfkMPNbhhGl-nE38JlKtpjRxRPTSE4iRVWkhxCNYqfLUnouqXON6xAwHUvQcVXNTm3evE9mW_kDd8nvUPDEeKRGly3YGRoaB-GnLwX0ZqJEyIpGXj_-6RaHBiaazIdg2Un72r4Az9bzGB0rr2I9CC6bhBi47gMXC-pOBDnJhIRuRtXqj4TFPie-jhLcHXvQn_2VETIrSv961wrfP6F9VK_h-nJACUhT0hVCiqW1Bl8E5phy0e0VFnM8MCFvcAG8aOeNH7pkyRTz7MWg")

# URL ajustada com o formato correto de usuário para Pooler: postgres.ID_DO_PROJETO
SUPABASE_URL = "postgresql+psycopg2://postgres.mwdhclwookhpwzrhfjjp:Romeuzinho22@aws-1-us-east-2.pooler.supabase.com:6543/postgres?sslmode=require"

# ==========================================
# 2. CONEXÃO COM BANCO DE DADOS
# ==========================================
print("🔗 Conectando ao Supabase na região US-East-2 via Pooler...")
engine = create_engine(SUPABASE_URL, pool_pre_ping=True, pool_recycle=300)

query_criar_tabela = """
CREATE TABLE IF NOT EXISTS leads_kommo (
    id BIGINT PRIMARY KEY,
    nome VARCHAR(255),
    valor NUMERIC(15,2),
    status_id BIGINT,
    pipeline_id BIGINT,
    responsible_user_id BIGINT,
    created_at TIMESTAMP,
    closed_at TIMESTAMP,
    updated_at TIMESTAMP,
    contact_id BIGINT,
    raw_custom_fields JSONB
);

ALTER TABLE leads_kommo ADD COLUMN IF NOT EXISTS contact_id BIGINT;
"""

with engine.connect() as conn:
    conn.execute(text(query_criar_tabela))
    conn.commit()
print("✅ Tabela 'leads_kommo' pronta no Supabase!")

# ==========================================
# 3. EXTRAÇÃO E CARGA
# ==========================================
headers = {"Authorization": f"Bearer {KOMMO_TOKEN}"}
pagina = 1
total_salvos = 0

print("🚀 Retomando busca e envio dos leads (com contatos) para o Supabase...\n")

while True:
    url_leads = f"https://{KOMMO_SUBDOMAIN}.kommo.com/api/v4/leads?limit=250&page={pagina}&with=contacts"
    res = requests.get(url_leads, headers=headers)
    
    if res.status_code == 204 or res.status_code != 200:
        break
        
    dados = res.json()
    leads = dados["_embedded"]["leads"]
    
    query_insert = """
    INSERT INTO leads_kommo (id, nome, valor, status_id, pipeline_id, responsible_user_id, created_at, closed_at, updated_at, contact_id, raw_custom_fields)
    VALUES (:id, :nome, :valor, :status_id, :pipeline_id, :responsible_user_id, :created_at, :closed_at, :updated_at, :contact_id, :raw_custom_fields)
    ON CONFLICT (id) DO UPDATE SET
        nome = EXCLUDED.nome,
        valor = EXCLUDED.valor,
        status_id = EXCLUDED.status_id,
        pipeline_id = EXCLUDED.pipeline_id,
        responsible_user_id = EXCLUDED.responsible_user_id,
        closed_at = EXCLUDED.closed_at,
        updated_at = EXCLUDED.updated_at,
        contact_id = EXCLUDED.contact_id,
        raw_custom_fields = EXCLUDED.raw_custom_fields;
    """
    
    registros = []
    for l in leads:
        created_at = datetime.fromtimestamp(l["created_at"]) if l.get("created_at") else None
        closed_at = datetime.fromtimestamp(l["closed_at"]) if l.get("closed_at") else None
        updated_at = datetime.fromtimestamp(l["updated_at"]) if l.get("updated_at") else None
        
        embedded_contacts = l.get("_embedded", {}).get("contacts", [])
        contact_id = embedded_contacts[0]["id"] if embedded_contacts else None

        custom_fields = json.dumps(l.get("custom_fields_values") or [])

        registros.append({
            "id": l["id"],
            "nome": l.get("name", "Sem nome"),
            "valor": l.get("price", 0),
            "status_id": l.get("status_id"),
            "pipeline_id": l.get("pipeline_id"),
            "responsible_user_id": l.get("responsible_user_id"),
            "created_at": created_at,
            "closed_at": closed_at,
            "updated_at": updated_at,
            "contact_id": contact_id,
            "raw_custom_fields": custom_fields
        })

    with engine.begin() as conn:
        conn.execute(text(query_insert), registros)

    total_salvos += len(leads)
    print(f"📦 Página {pagina}: +{len(leads)} leads processados (Total acumulado: {total_salvos})")

    if "next" not in dados.get("_links", {}):
        break
        
    pagina += 1

print(f"\n🎉 Sucesso Total! Todos os {total_salvos} leads atualizados com IDs de contatos!")
