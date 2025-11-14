Projeto TCC: Análise de Soja com YOLOv8 e WebRTC

Este projeto é uma API em FastAPI (Python 3.9) que utiliza um modelo YOLOv8 para a deteção e contagem de plantas de soja em tempo real (via WebRTC) e através de upload de vídeos.

Arquitetura de Execução (Este Ramo):

Backend: API FastAPI (Local)

Ambiente: Python 3.9 (Venv)

Banco de Dados: PostgreSQL (Serviço Local na Porta 5432 ou 5200)

🚀 Guia de Instalação Local (Sem Docker)

Siga estes passos para executar o projeto na sua máquina.

Passo 1: Pré-requisitos (Instalação Manual)

Estes programas devem ser instalados na máquina host:

Python 3.9:

Download (Windows 64-bit)

Importante: Durante a instalação, marque a caixa "Add Python 3.9 to PATH".

Git:

Baixar Git

PostgreSQL (O Banco de Dados):

Download (Windows x86-64) (Recomendado: Versão 15 ou 16).

Durante a Instalação:

Defina uma senha mestra para o utilizador postgres e anote-a.

Defina a Porta (Port). O padrão é 5432. Se você a mudar (ex: 5200), anote-a.

Após a Instalação (Usando pgAdmin 4):

Abra o pgAdmin 4 e ligue-se ao seu servidor local (com a senha mestra).

No painel esquerdo, clique com o botão direito em "Databases" > "Create" > "Database...".

No campo "Database name", digite: tcc_soja.

(Opcional, se usar soja_api): Crie um "Login Role" (Utilizador) chamado soja_api com a senha root. Se não, use o utilizador postgres padrão.

Passo 2: Configurar o Projeto

Abra o seu Terminal (PowerShell ou Git Bash).

Clone o projeto (se ainda não o fez):

git clone [https://github.com/LNeto82/tcc.git](https://github.com/LNeto82/tcc.git)


Entre na pasta do projeto:

cd tcc


(Ou cd soyplant-detect-api-main, dependendo do nome da pasta)

Passo 3: Configurar o Ambiente Python (Venv)

Crie o ambiente virtual:

python -m venv venv


Ative o ambiente virtual:

.\venv\Scripts\Activate.ps1


(O seu terminal deve agora mostrar (venv))

Instale todas as dependências do projeto:

pip install -r requirements.txt


Passo 4: Configurar o .env (A Chave de Conexão)

Este é o passo mais importante.

Na raiz do projeto, crie um arquivo chamado .env.

Copie e cole o seguinte conteúdo, ajustando os valores para o seu PostgreSQL (que você instalou no Passo 1.3):

# Configuração para rodar LOCALMENTE (sem Docker)

# (Use 'localhost' se o banco estiver na sua máquina)
DB_HOST=localhost

# (Use a porta que você configurou. Padrão é 5432)
DB_PORT=5432

# (O nome do banco que você criou no pgAdmin)
DB_NAME=tcc_soja

# (O utilizador do seu Postgres)
DB_USER=postgres

# (A senha mestra que você definiu na instalação do Postgres)
DB_PASSWORD=SUA_SENHA_MESTRA_AQUI


Passo 5: Executar o Projeto

Agora que o Postgres está a rodar e o .env está correto:

Verifique se o seu (venv) está ativo.

Execute o servidor Uvicorn a partir da pasta raiz do projeto:

python -m uvicorn src.yoloDetectionV3.main:app --reload --host 0.0.0.0 --port 8000


Aguarde até ver as mensagens de sucesso:
[SUCESSO] Tabelas do banco de dados prontas.
INFO:src.yoloDetectionV3.services.yolo_service:Modelo YOLO carregado com sucesso.
Uvicorn running on http://0.0.0.0:8000

Acesso

A aplicação está pronta! Abra o seu navegador e acesse:

http://localhost:8000/interface

eof

---

### Passo 3: Subir para o Git (O Checkpoint)

Agora que você tem o `.gitignore` e o `README.md` atualizados:

1.  No seu terminal (na pasta raiz), adicione os novos arquivos e todas as suas correções de código:
    ```bash
    git add .
    ```
2.  Faça o "commit" (o snapshot) da sua versão funcional:
    ```bash
    git commit -m "Checkpoint: Versão Local 100% Funcional (Py3.9 + LocalDB + WebRTC)"
    ```
3.  Envie o seu checkpoint para o GitHub:
    ```bash
    git push origin main
