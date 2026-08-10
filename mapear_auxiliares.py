import requests
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

# ==========================================
# 1. CONFIGURAÇÕES
# ==========================================
KOMMO_SUBDOMAIN = "miletobr"
KOMMO_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImp0aSI6IjVmOTZlYTFlNDJkYmM1YWIzN2FjMmVhMjFkOWExMWE5NTRmNjEzZTFjZTI4Y2M2NzE3M2EzNTYyOTY3NDRiMmNjNDRhYjZmOWRjOTdmYWNjIn0.eyJhdWQiOiI2MzM4MDNjNC0zNDVmLTQ1NDItOWY5ZS0zMDk3MTZmMjM5NjAiLCJqdGkiOiI1Zjk2ZWExZTQyZGJjNWFiMzdhYzJlYTIxZDlhMTFhOTU0ZjYxM2UxY2UyOGNjNjcxNzNhMzU2Mjk2NzQ0YjJjYzQ0YWI2ZjlkYzk3ZmFjYyIsImlhdCI6MTc4NDcyNjU3MCwibmJmIjoxNzg0NzI2NTcwLCJleHAiOjE4MzAyMTEyMDAsInN1YiI6IjE0NTUyODM1IiwiZ3JhbnRfdHlwZSI6IiIsImFjY291bnRfaWQiOjM1ODU3OTgzLCJiYXNlX2RvbWFpbiI6ImtvbW1vLmNvbSIsInZlcnNpb24iOjIsInNjb3BlcyI6WyJwdXNoX25vdGlmaWNhdGlvbnMiLCJmaWxlcyIsImNybSIsImZpbGVzX2RlbGV0ZSIsIm5vdGlmaWNhdGlvbnMiXSwiaGFzaF91dWlkIjoiYjU4MWQxZDMtYTcxNS00YzRmLTkwMDctZTYwYmI1MzlmMTdmIiwiYXBpX2RvbWFpbiI6ImFwaS1jLmtvbW1vLmNvbSJ9.RBFF1wCgOF8wdTqPLXpabe4LL0boXQ8CZ89ovXzbZiTDbS_vdVmRjQwMHeMLaGixJy54TiVpTNScqzmg1BR2wiaonJya3FcxiqqfZIdIlx6QRNZnzDU2FqMRGfwGKDxrpuuewpv0crDrSjTLfF5sLb1kAPYYnrnWl73iKr2gxTzDLjmAdn9SRKWhpBTUH78rsSR4kTTAiEdtKdAJCNkJus6IIdHc6rKRsvuj25HmWuv0arX3MpBFZEv2ghMGOZQrwYwX5XbXhxEaMz43XpDP-o3yOAv4rcOG929NeW0foUDpR7ysCScMeSbPQp5GuKHU3d0hj6iD0qllfiAmtfDfVw"

senha_segura = quote_plus("Cafe2021@@*")

# AJUSTADO: Conexão via Pooler do Supabase (suporta IPv4 do GitHub Actions)
USER = "postgres.mwdhclwookhpwzrhfjjp"
HOST = "aws-0-sa-east-1.pooler.supabase.com"
PORT = "6543"
DBNAME = "postgres"

SUPABASE_URL = f"postgresql+psycopg2://{USER}:{senha_segura}@{HOST}:{PORT}/{DBNAME}?sslmode=require&connect_timeout=30"

engine = create_engine(SUPABASE_URL, pool_pre_ping=True)
headers = {"Authorization": f"Bearer {KOMMO_TOKEN}"}

# ==========================================
# 2. CRIAR TABELAS AUXILIARES
# ==========================================
print("🔗 Conectando ao Supabase para criar tabelas de apoio...")

query_tabelas = """
CREATE TABLE IF NOT EXISTS usuarios_kommo (
    id BIGINT PRIMARY KEY,
    nome VARCHAR(255),
    email VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS etapas_kommo (
    status_id BIGINT PRIMARY KEY,
    nome_etapa VARCHAR(255),
    pipeline_id BIGINT,
    nome_pipeline VARCHAR(255)
);
"""

with engine.begin() as conn:
    conn.execute(text(query_tabelas))
print("✅ Tabelas 'usuarios_kommo' e 'etapas_kommo' criadas com sucesso!")

# ==========================================
# 3. Mapear Usuários / Vendedores
# ==========================================
print("👥 Buscando Vendedores na Kommo...")
url_users = f"https://{KOMMO_SUBDOMAIN}.kommo.com/api/v4/users"
res_users = requests.get(url_users, headers=headers)

if res_users.status_code == 200:
    users_data = res_users.json()["_embedded"]["users"]
    list_users = []
    for u in users_data:
        list_users.append({
            "id": u["id"],
            "nome": u["name"],
            "email": u.get("email", "")
        })
    
    query_users = """
    INSERT INTO usuarios_kommo (id, nome, email)
    VALUES (:id, :nome, :email)
    ON CONFLICT (id) DO UPDATE SET nome = EXCLUDED.nome, email = EXCLUDED.email;
    """
    with engine.begin() as conn:
        conn.execute(text(query_users), list_users)
    print(f"✅ {len(list_users)} Vendedores cadastrados/atualizados!")

# ==========================================
# 4. Mapear Funis e Etapas
# ==========================================
print("📈 Buscando Funis e Etapas na Kommo...")
url_pipelines = f"https://{KOMMO_SUBDOMAIN}.kommo.com/api/v4/leads/pipelines"
res_pipelines = requests.get(url_pipelines, headers=headers)

if res_pipelines.status_code == 200:
    pipelines_data = res_pipelines.json()["_embedded"]["pipelines"]
    list_etapas = []
    
    for pipe in pipelines_data:
        p_id = pipe["id"]
        p_name = pipe["name"]
        
        statuses = pipe["_embedded"]["statuses"]
        for st in statuses:
            list_etapas.append({
                "status_id": st["id"],
                "nome_etapa": st["name"],
                "pipeline_id": p_id,
                "nome_pipeline": p_name
            })
            
    query_etapas = """
    INSERT INTO etapas_kommo (status_id, nome_etapa, pipeline_id, nome_pipeline)
    VALUES (:status_id, :nome_etapa, :pipeline_id, :nome_pipeline)
    ON CONFLICT (status_id) DO UPDATE SET 
        nome_etapa = EXCLUDED.nome_etapa,
        pipeline_id = EXCLUDED.pipeline_id,
        nome_pipeline = EXCLUDED.nome_pipeline;
    """
    with engine.begin() as conn:
        conn.execute(text(query_etapas), list_etapas)
    print(f"✅ {len(list_etapas)} Etapas/Status cadastrados/atualizados!")

print("\n🎉 Mapeamento concluído com sucesso!")
# ==========================================
# 5. Mapear Contatos (Pessoas)
# ==========================================
print("👤 Buscando Contatos (Clientes) na Kommo...")

query_tabela_contatos = """
CREATE TABLE IF NOT EXISTS contatos_kommo (
    id BIGINT PRIMARY KEY,
    nome VARCHAR(255)
);
"""
with engine.begin() as conn:
    conn.execute(text(query_tabela_contatos))

pagina_contatos = 1
total_contatos = 0

while True:
    url_contacts = f"https://{KOMMO_SUBDOMAIN}.kommo.com/api/v4/contacts?limit=250&page={pagina_contatos}"
    res_contacts = requests.get(url_contacts, headers=headers)
    
    if res_contacts.status_code == 204 or res_contacts.status_code != 200:
        break
        
    contacts_data = res_contacts.json()["_embedded"]["contacts"]
    list_contacts = []
    
    for c in contacts_data:
        list_contacts.append({
            "id": c["id"],
            "nome": c.get("name", "Sem Nome")
        })
        
    query_contacts = """
    INSERT INTO contatos_kommo (id, nome)
    VALUES (:id, :nome)
    ON CONFLICT (id) DO UPDATE SET nome = EXCLUDED.nome;
    """
    
    with engine.begin() as conn:
        conn.execute(text(query_contacts), list_contacts)
        
    total_contatos += len(list_contacts)
    print(f"👤 Página {pagina_contatos}: +{len(list_contacts)} contatos cadastrados (Total: {total_contatos})")
    
    if "next" not in res_contacts.json().get("_links", {}):
        break
        
    pagina_contatos += 1

print(f"✅ {total_contatos} Contatos (Clientes) sincronizados com sucesso!")
