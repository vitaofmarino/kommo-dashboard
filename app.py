import os
import requests
import json
from datetime import datetime
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

# ==========================================
# 1. CONFIGURAÇÕES
# ==========================================
KOMMO_SUBDOMAIN = os.getenv("KOMMO_SUBDOMAIN", "miletobr")
KOMMO_TOKEN = os.getenv("KOMMO_ACCESS_TOKEN", "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImp0aSI6IjVmOTZlYTFlNDJkYmM1YWIzN2FjMmVhMjFkOWExMWE5NTRmNjEzZTFjZTI4Y2M2NzE3M2EzNTYyOTY3NDRiMmNjNDRhYjZmOWRjOTdmYWNjIn0.eyJhdWQiOiI2MzM4MDNjNC0zNDVmLTQ1NDItOWY5ZS0zMDk3MTZmMjM5NjAiLCJqdGkiOiI1Zjk2ZWExZTQyZGJjNWFiMzdhYzJlYTIxZDlhMTFhOTU0ZjYxM2UxY2UyOGNjNjcxNzNhMzU2Mjk2NzQ0YjJjYzQ0YWI2ZjlkYzk3ZmFjYyIsImlhdCI6MTc4NDcyNjU3MCwibmJmIjoxNzg0NzI2NTcwLCJleHAiOjE4MzAyMTEyMDAsInN1YiI6IjE0NTUyODM1IiwiZ3JhbnRfdHlwZSI6IiIsImFjY291bnRfaWQiOjM1ODU3OTgzLCJiYXNlX2RvbWFpbiI6ImtvbW1vLmNvbSIsInZlcnNpb24iOjIsInNjb3BlcyI6WyJwdXNoX25vdGlmaWNhdGlvbnMiLCJmaWxlcyIsImNybSIsImZpbGVzX2RlbGV0ZSIsIm5vdGlmaWNhdGlvbnMiXSwiaGFzaF91dWlkIjoiYjU4MWQxZDMtYTcxNS00YzRmLTkwMDctZTYwYmI1MzlmMTdmIiwiYXBpX2RvbWFpbiI6ImFwaS1jLmtvbW1vLmNvbSJ9.RBFF1wCgOF8wdTqPLXpabe4LL0boXQ8CZ89ovXzbZiTDbS_vdVmRjQwMHeMLaGixJy54TiVpTNScqzmg1BR2wiaonJya3FcxiqqfZIdIlx6QRNZnzDU2FqMRGfwGKDxrpuuewpv0crDrSjTLfF5sLb1kAPYYnrnWl73iKr2gxTzDLjmAdn9SRKWhpBTUH78rsSR4kTTAiEdtKdAJCNkJus6IIdHc6rKRsvuj25HmWuv0arX3MpBFZEv2ghMGOZQrwYwX5XbXhxEaMz43XpDP-o3yOAv4rcOG929NeW0foUDpR7ysCScMeSbPQp5GuKHU3d0hj6iD0qllfiAmtfDfVw")

# Senha nova tratada corretamente contra os colchetes
SENHA_PURA = "[Romeuzinho24]"
senha_segura = quote_plus(SENHA_PURA)

# Configuração limpa baseada na sua URL original
USER = "postgres"
HOST = "db.mwdhclwookhpwzrhfjjp.supabase.co"
PORT = "5432"
DBNAME = "postgres"

# Forçamos a URL diretamente no código para ignorar qualquer lixo que tenha ficado no GitHub Secrets
SUPABASE_URL = f"postgresql+psycopg2://{USER}:{senha_segura}@{HOST}:{PORT}/{DBNAME}?sslmode=require"

# ==========================================
# 2. CONEXÃO COM BANCO DE DADOS
# ==========================================
print("🔗 Conectando ao Supabase...")
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
