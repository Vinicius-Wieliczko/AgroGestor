from flask import Flask, render_template, request, jsonify
import sqlite3
import smtplib
import hashlib
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__, template_folder='.', static_folder='.', static_url_path='')

app.secret_key = "chave-secreta-agrogestor"
serializer = URLSafeTimedSerializer(app.secret_key)

# ==========================================
# CONFIGURAÇÃO DO BANCO DE DADOS
# ==========================================
DB_NAME = 'agrogestor.db' 

def get_db_connection():
    conn = sqlite3.connect(DB_NAME, timeout=10)
    conn.row_factory = sqlite3.Row 
    conn.execute('PRAGMA foreign_keys = ON;')
    return conn

@app.route('/')
def index():
    return render_template('index.html')

# ==========================================
# 1. AUTENTICAÇÃO E PERFIL
# ==========================================
@app.route('/api/cadastro', methods=['POST'])
def cadastro():
    dados = request.get_json()
    senha_hash = generate_password_hash(dados['senha'])
    cpf_hash = hashlib.sha256(dados['cpf'].encode('utf-8')).hexdigest()
    
    try:
        conn = get_db_connection()
        conn.execute('INSERT INTO usuario (nome_completo, email, cpf, senha, estado) VALUES (?, ?, ?, ?, ?)', 
                     (dados['nome'], dados['email'], cpf_hash, senha_hash, dados['estado']))
        conn.commit()
        conn.close()
        return jsonify({'sucesso': True, 'mensagem': 'Cadastro realizado com sucesso!'})
    except sqlite3.IntegrityError:
        return jsonify({'sucesso': False, 'mensagem': 'Erro: CPF ou E-mail já cadastrados.'})

@app.route('/api/login', methods=['POST'])
def login():
    dados = request.get_json()
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM usuario WHERE email = ?', (dados['email'],)).fetchone()
    conn.close()
    
    if user and check_password_hash(user['senha'], dados['senha']): 
        usuario_dict = dict(user)
        del usuario_dict['senha']
        del usuario_dict['cpf']
        return jsonify({'sucesso': True, 'usuario': usuario_dict})
    else: 
        return jsonify({'sucesso': False, 'mensagem': 'E-mail ou senha incorretos.'})

@app.route('/api/perfil/<int:id_usuario>', methods=['PUT'])
def atualizar_perfil(id_usuario):
    dados = request.get_json()
    try:
        conn = get_db_connection()
        conn.execute('UPDATE usuario SET nome_completo = ?, estado = ? WHERE id = ?', 
                     (dados['nome'], dados['estado'], id_usuario))
        conn.commit()
        conn.close()
        return jsonify({'sucesso': True, 'mensagem': 'Perfil salvo com sucesso no banco de dados!'})
    except Exception as e:
        return jsonify({'sucesso': False, 'mensagem': f'Erro: {str(e)}'})

# ==========================================
# RECUPERAÇÃO DE SENHA VIA LINK 
# ==========================================
@app.route('/api/recuperar_senha', methods=['POST'])
def recuperar_senha():
    dados = request.get_json()
    email_digitado = dados.get('email')
    cpf_digitado = dados.get('cpf')

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM usuario WHERE email = ?', (email_digitado,)).fetchone()
    conn.close()

    if not user:
        return jsonify({'sucesso': False, 'mensagem': 'E-mail não encontrado no sistema.'})

    cpf_hash_digitado = hashlib.sha256(cpf_digitado.encode('utf-8')).hexdigest()
    if user['cpf'] != cpf_hash_digitado:
        return jsonify({'sucesso': False, 'mensagem': 'O CPF não corresponde ao cadastrado para este e-mail.'})

    token = serializer.dumps(email_digitado, salt='recuperacao-senha')
    link_recuperacao = f"{request.host_url}?token={token}"

    nome_do_usuario = user['nome_completo']
    
    meu_email = "suporte.agrogestor@gmail.com" 
    minha_senha = "olwy kzws dlwd obia" 

    msg = MIMEMultipart()
    msg['From'] = meu_email
    msg['To'] = email_digitado
    msg['Subject'] = "Recuperação de Senha - AgroGestor"

    corpo_email = f"Olá {nome_do_usuario},\n\nVocê solicitou a recuperação de senha no AgroGestor.\n\nClique no link abaixo para criar uma nova senha:\n{link_recuperacao}\n\nEste link expira em 1 hora."
    msg.attach(MIMEText(corpo_email, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(meu_email, minha_senha)
        server.send_message(msg)
        server.quit()
        return jsonify({'sucesso': True, 'mensagem': 'Um link de recuperação foi enviado para o seu e-mail!'})
    except Exception as e:
        return jsonify({'sucesso': False, 'mensagem': 'Erro ao enviar o e-mail. Verifique o terminal do Python.'})

@app.route('/api/nova_senha', methods=['POST'])
def nova_senha():
    dados = request.get_json()
    token = dados.get('token')
    nova_senha = dados.get('senha')

    try:
        email = serializer.loads(token, salt='recuperacao-senha', max_age=3600)
    except:
        return jsonify({'sucesso': False, 'mensagem': 'O link de recuperação é inválido ou expirou.'})

    senha_hash = generate_password_hash(nova_senha)
    conn = get_db_connection()
    conn.execute('UPDATE usuario SET senha = ? WHERE email = ?', (senha_hash, email))
    conn.commit()
    conn.close()
    
    return jsonify({'sucesso': True, 'mensagem': 'Sua senha foi alterada com sucesso! Faça login.'})

# ==========================================
# 2. PLANTAÇÃO
# ==========================================
@app.route('/api/plantacao', methods=['POST'])
def nova_plantacao():
    dados = request.get_json()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO plantacao (nome, area, data_plantio, data_colheita, id_usuario) VALUES (?, ?, ?, ?, ?)', 
                   (dados['nome'], dados['area'], dados['plantio'], dados['colheita'], dados['id_usuario']))
    conn.commit()
    novo_id = cursor.lastrowid
    conn.close()
    return jsonify({'sucesso': True, 'id': novo_id})

@app.route('/api/plantacoes/<int:id_usuario>', methods=['GET'])
def listar_plantacoes(id_usuario):
    conn = get_db_connection()
    plantacoes = conn.execute('SELECT * FROM plantacao WHERE id_usuario = ?', (id_usuario,)).fetchall()
    conn.close()
    return jsonify([dict(p) for p in plantacoes])

@app.route('/api/plantacao/<int:id_plantacao>', methods=['DELETE'])
def deletar_plantacao(id_plantacao):
    conn = get_db_connection()
    conn.execute('DELETE FROM plantacao WHERE id = ?', (id_plantacao,))
    conn.commit()
    conn.close()
    return jsonify({'sucesso': True})

# ==========================================
# 3. FINANÇAS
# ==========================================
@app.route('/api/financas', methods=['POST'])
def add_financa():
    dados = request.get_json()
    conn = get_db_connection()
    conn.execute('INSERT INTO financas (tipo, valor, id_usuario) VALUES (?, ?, ?)', 
                 (dados['tipo'], dados['valor'], dados['id_usuario']))
    conn.commit()
    conn.close()
    return jsonify({'sucesso': True})

@app.route('/api/financas/<int:id_usuario>', methods=['GET'])
def get_financas(id_usuario):
    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM financas WHERE id_usuario = ?', (id_usuario,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

# ==========================================
# 4. INSUMOS (Com nova lógica de Lotes)
# ==========================================
@app.route('/api/insumo_estoque', methods=['POST'])
def add_estoque():
    dados = request.get_json()
    conn = get_db_connection()
    existente = conn.execute('SELECT * FROM insumo_estoque WHERE registro = ? AND validadeRaw = ? AND id_usuario = ?',
                             (dados['registro'], dados['validadeRaw'], dados['id_usuario'])).fetchone()
    
    if existente:
        conn.execute('UPDATE insumo_estoque SET quantidade = quantidade + ? WHERE id = ?', (dados['qtd'], existente['id']))
    else:
        conn.execute('INSERT INTO insumo_estoque (nome, quantidade, unidade, registro, validade, validadeRaw, id_usuario) VALUES (?, ?, ?, ?, ?, ?, ?)',
                     (dados['nome'], dados['qtd'], dados['unidade'], dados['registro'], dados['validade'], dados['validadeRaw'], dados['id_usuario']))
    conn.commit()
    conn.close()
    return jsonify({'sucesso': True})

# Rota para o produtor conseguir buscar o lote tanto por nome quanto por registro
@app.route('/api/insumo_estoque/busca/<int:id_usuario>', methods=['GET'])
def buscar_lotes(id_usuario):
    termo = request.args.get('q', '').lower()
    conn = get_db_connection()
    query = '''SELECT * FROM insumo_estoque 
               WHERE id_usuario = ? AND (LOWER(nome) LIKE ? OR registro LIKE ?)'''
    lotes = conn.execute(query, (id_usuario, f'%{termo}%', f'%{termo}%')).fetchall()
    conn.close()
    return jsonify([dict(l) for l in lotes])

@app.route('/api/insumo_uso', methods=['POST'])
def add_uso():
    try:
        dados = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        lotes_usados = dados.get('lotes', [])
        if not lotes_usados:
            return jsonify({'sucesso': False, 'mensagem': 'Nenhum insumo selecionado.'})
            
        # Percorre todos os lotes que o produtor digitou na tela
        for lote in lotes_usados:
            id_estoque = lote['id']
            qtd_usada = float(lote['qtdUsada'])
            
            insumo = cursor.execute('SELECT * FROM insumo_estoque WHERE id = ? AND id_usuario = ?', 
                                  (id_estoque, dados['id_usuario'])).fetchone()
            
            if not insumo:
                conn.rollback()
                return jsonify({'sucesso': False, 'mensagem': 'Um dos insumos não foi encontrado!'})
                
            if insumo['quantidade'] < qtd_usada:
                conn.rollback()
                return jsonify({'sucesso': False, 'mensagem': f'Estoque insuficiente para {insumo["nome"]}.'})

            nova_qtd = insumo['quantidade'] - qtd_usada
            if nova_qtd <= 0: 
                cursor.execute('DELETE FROM insumo_estoque WHERE id = ?', (id_estoque,))
            else: 
                cursor.execute('UPDATE insumo_estoque SET quantidade = ? WHERE id = ?', (nova_qtd, id_estoque))

            cursor.execute('INSERT INTO insumo_uso (nome, quantidade_usada, unidade, local_nome, data_uso, id_usuario, id_plantacao) VALUES (?, ?, ?, ?, ?, ?, ?)',
                         (insumo['nome'], qtd_usada, insumo['unidade'], dados['local_nome'], dados['dataUso'], dados['id_usuario'], dados['id_plantacao']))

        conn.commit()
        conn.close()
        return jsonify({'sucesso': True})
    except Exception as e:
        return jsonify({'sucesso': False, 'mensagem': f'Erro interno do servidor: {str(e)}'})

@app.route('/api/insumo_estoque/<int:id_insumo>', methods=['DELETE'])
def deletar_insumo_estoque(id_insumo):
    conn = get_db_connection()
    conn.execute('DELETE FROM insumo_estoque WHERE id = ?', (id_insumo,))
    conn.commit()
    conn.close()
    return jsonify({'sucesso': True})

@app.route('/api/insumos/<int:id_usuario>', methods=['GET'])
def get_insumos(id_usuario):
    conn = get_db_connection()
    estoque = conn.execute('SELECT * FROM insumo_estoque WHERE id_usuario = ?', (id_usuario,)).fetchall()
    em_uso = conn.execute('SELECT * FROM insumo_uso WHERE id_usuario = ?', (id_usuario,)).fetchall()
    conn.close()
    return jsonify({'estoque': [dict(r) for r in estoque], 'em_uso': [dict(r) for r in em_uso]})

if __name__ == '__main__':
    app.run(debug=True)