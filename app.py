import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import smtplib
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from functools import wraps

from flask import Flask, jsonify, render_template, request, session
from itsdangerous import URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash


app = Flask(__name__, template_folder='.', static_folder='.', static_url_path='')

def load_secret_key():
    env_secret = os.environ.get('AGROGESTOR_SECRET_KEY')
    if env_secret:
        return env_secret

    secret_path = '.agrogestor_secret'
    if os.path.exists(secret_path):
        with open(secret_path, 'r', encoding='utf-8') as file:
            return file.read().strip()

    secret = secrets.token_hex(32)
    with open(secret_path, 'w', encoding='utf-8') as file:
        file.write(secret)
    return secret


app.secret_key = load_secret_key()
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=False,
    JSON_SORT_KEYS=False,
)
serializer = URLSafeTimedSerializer(app.secret_key)

DB_NAME = 'agrogestor.db'
ESTADOS_BR = {
    'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS',
    'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC',
    'SP', 'SE', 'TO'
}
UNIDADES_INSUMO = {'Kg', 'L'}
MAX_TEXT = 120
LOGIN_ATTEMPTS = {}


def get_db_connection():
    conn = sqlite3.connect(DB_NAME, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON;')
    return conn


def json_error(message, status=400):
    return jsonify({'sucesso': False, 'mensagem': message}), status


@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get('usuario_id'):
            return json_error('Sessao expirada. Faca login novamente.', 401)
        return view(*args, **kwargs)
    return wrapped


def current_user_id():
    return int(session['usuario_id'])


def get_json_payload():
    dados = request.get_json(silent=True)
    if not isinstance(dados, dict):
        raise ValueError('Envie dados em formato JSON.')
    return dados


def normalize_spaces(value):
    return re.sub(r'\s+', ' ', str(value or '')).strip()


def validate_text(value, field, min_len=2, max_len=MAX_TEXT):
    text = normalize_spaces(value)
    if len(text) < min_len:
        raise ValueError(f'{field} deve ter pelo menos {min_len} caracteres.')
    if len(text) > max_len:
        raise ValueError(f'{field} deve ter no maximo {max_len} caracteres.')
    if re.search(r'[<>{}]', text):
        raise ValueError(f'{field} contem caracteres nao permitidos.')
    return text


def validate_email(value):
    email = normalize_spaces(value).lower()
    if len(email) > 254 or not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', email):
        raise ValueError('Informe um e-mail valido.')
    return email


def only_digits(value):
    return re.sub(r'\D', '', str(value or ''))


def validate_cpf(value):
    cpf = only_digits(value)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        raise ValueError('Informe um CPF valido.')

    def digit(numbers):
        total = sum(int(num) * weight for num, weight in zip(numbers, range(len(numbers) + 1, 1, -1)))
        rest = (total * 10) % 11
        return 0 if rest == 10 else rest

    if digit(cpf[:9]) != int(cpf[9]) or digit(cpf[:10]) != int(cpf[10]):
        raise ValueError('Informe um CPF valido.')
    return cpf


def cpf_fingerprint(cpf):
    pepper = app.secret_key.encode('utf-8')
    return hmac.new(pepper, cpf.encode('utf-8'), hashlib.sha256).hexdigest()


def legacy_cpf_hash(cpf):
    return hashlib.sha256(cpf.encode('utf-8')).hexdigest()


def previous_dev_cpf_hash(cpf):
    return hmac.new(
        b'dev-secret-change-before-production',
        cpf.encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()


def validate_password(password):
    password = str(password or '')
    if len(password) < 8:
        raise ValueError('A senha deve ter pelo menos 8 caracteres.')
    if len(password) > 128:
        raise ValueError('A senha deve ter no maximo 128 caracteres.')
    if not re.search(r'[A-Za-z]', password) or not re.search(r'\d', password):
        raise ValueError('A senha deve conter letras e numeros.')
    return password


def validate_estado(value):
    estado = normalize_spaces(value).upper()
    if estado not in ESTADOS_BR:
        raise ValueError('Selecione um estado valido.')
    return estado


def validate_positive_float(value, field, max_value=999999999):
    try:
        number = round(float(value), 2)
    except (TypeError, ValueError):
        raise ValueError(f'{field} deve ser um numero valido.')
    if number <= 0 or number > max_value:
        raise ValueError(f'{field} deve ser maior que zero.')
    return number


def validate_date(value, field):
    value = normalize_spaces(value)
    try:
        datetime.strptime(value, '%Y-%m-%d')
    except ValueError:
        raise ValueError(f'{field} deve ser uma data valida.')
    return value


def validate_br_date(value, field):
    value = normalize_spaces(value)
    try:
        datetime.strptime(value, '%d/%m/%Y')
    except ValueError:
        raise ValueError(f'{field} deve ser uma data valida.')
    return value


def public_user(row):
    return {
        'id': row['id'],
        'nome_completo': row['nome_completo'],
        'email': row['email'],
        'estado': row['estado'],
    }


def too_many_login_attempts(email):
    now = time.time()
    attempts = [t for t in LOGIN_ATTEMPTS.get(email, []) if now - t < 300]
    LOGIN_ATTEMPTS[email] = attempts
    return len(attempts) >= 5


def record_login_failure(email):
    LOGIN_ATTEMPTS.setdefault(email, []).append(time.time())


def clear_login_failures(email):
    LOGIN_ATTEMPTS.pop(email, None)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/sessao', methods=['GET'])
def sessao_atual():
    usuario_id = session.get('usuario_id')
    if not usuario_id:
        return jsonify({'sucesso': False})
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM usuario WHERE id = ?', (usuario_id,)).fetchone()
    conn.close()
    if not user:
        session.clear()
        return jsonify({'sucesso': False})
    return jsonify({'sucesso': True, 'usuario': public_user(user)})


@app.route('/api/cadastro', methods=['POST'])
def cadastro():
    try:
        dados = get_json_payload()
        nome = validate_text(dados.get('nome'), 'Nome completo', 3)
        email = validate_email(dados.get('email'))
        cpf = validate_cpf(dados.get('cpf'))
        senha = validate_password(dados.get('senha'))
        estado = validate_estado(dados.get('estado'))
    except ValueError as exc:
        return json_error(str(exc))

    senha_hash = generate_password_hash(senha)
    cpf_hash = cpf_fingerprint(cpf)
    cpf_hash_legado = legacy_cpf_hash(cpf)

    try:
        conn = get_db_connection()
        duplicado = conn.execute(
            'SELECT id FROM usuario WHERE email = ? OR cpf IN (?, ?, ?)',
            (email, cpf_hash, cpf_hash_legado, previous_dev_cpf_hash(cpf)),
        ).fetchone()
        if duplicado:
            conn.close()
            return json_error('CPF ou e-mail ja cadastrados.', 409)
        conn.execute(
            'INSERT INTO usuario (nome_completo, email, cpf, senha, estado) VALUES (?, ?, ?, ?, ?)',
            (nome, email, cpf_hash, senha_hash, estado),
        )
        conn.commit()
        conn.close()
        return jsonify({'sucesso': True, 'mensagem': 'Cadastro realizado com sucesso!'})
    except sqlite3.IntegrityError:
        return json_error('CPF ou e-mail ja cadastrados.', 409)


@app.route('/api/login', methods=['POST'])
def login():
    try:
        dados = get_json_payload()
        email = validate_email(dados.get('email'))
        senha = str(dados.get('senha') or '')
    except ValueError:
        return json_error('E-mail ou senha incorretos.', 401)

    if too_many_login_attempts(email):
        return json_error('Muitas tentativas. Aguarde alguns minutos antes de tentar novamente.', 429)

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM usuario WHERE email = ?', (email,)).fetchone()
    conn.close()

    if user and check_password_hash(user['senha'], senha):
        session.clear()
        session['usuario_id'] = user['id']
        clear_login_failures(email)
        return jsonify({'sucesso': True, 'usuario': public_user(user)})

    record_login_failure(email)
    return json_error('E-mail ou senha incorretos.', 401)


@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'sucesso': True})


@app.route('/api/perfil/<int:id_usuario>', methods=['PUT'])
@login_required
def atualizar_perfil(id_usuario):
    if id_usuario != current_user_id():
        return json_error('Voce nao tem permissao para editar este perfil.', 403)
    try:
        dados = get_json_payload()
        nome = validate_text(dados.get('nome'), 'Nome completo', 3)
        estado = validate_estado(dados.get('estado'))
    except ValueError as exc:
        return json_error(str(exc))

    conn = get_db_connection()
    conn.execute('UPDATE usuario SET nome_completo = ?, estado = ? WHERE id = ?', (nome, estado, id_usuario))
    conn.commit()
    conn.close()
    return jsonify({'sucesso': True, 'mensagem': 'Perfil salvo com sucesso!'})


@app.route('/api/recuperar_senha', methods=['POST'])
def recuperar_senha():
    try:
        dados = get_json_payload()
        email_digitado = validate_email(dados.get('email'))
        cpf_digitado = validate_cpf(dados.get('cpf'))
    except ValueError as exc:
        return json_error(str(exc))

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM usuario WHERE email = ?', (email_digitado,)).fetchone()
    conn.close()

    if not user:
        return json_error('E-mail nao encontrado no sistema.', 404)

    cpf_valido = user['cpf'] in {
        cpf_fingerprint(cpf_digitado),
        legacy_cpf_hash(cpf_digitado),
        previous_dev_cpf_hash(cpf_digitado),
    }
    if not cpf_valido:
        return json_error('O CPF nao corresponde ao cadastrado para este e-mail.', 403)

    token = serializer.dumps(email_digitado, salt='recuperacao-senha')
    link_recuperacao = f'{request.host_url}?token={token}'
    smtp_user = os.environ.get('AGROGESTOR_SMTP_EMAIL')
    smtp_password = os.environ.get('AGROGESTOR_SMTP_PASSWORD')

    if not smtp_user or not smtp_password:
        return json_error('Recuperacao por e-mail nao configurada neste ambiente.', 503)

    msg = MIMEMultipart()
    msg['From'] = smtp_user
    msg['To'] = email_digitado
    msg['Subject'] = 'Recuperacao de Senha - AgroGestor'
    corpo_email = (
        f'Ola {user["nome_completo"]},\n\n'
        'Voce solicitou a recuperacao de senha no AgroGestor.\n\n'
        f'Acesse o link abaixo para criar uma nova senha:\n{link_recuperacao}\n\n'
        'Este link expira em 1 hora.'
    )
    msg.attach(MIMEText(corpo_email, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=15)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
        return jsonify({'sucesso': True, 'mensagem': 'Um link de recuperacao foi enviado para o seu e-mail!'})
    except Exception:
        return json_error('Erro ao enviar o e-mail. Verifique a configuracao SMTP.', 502)


@app.route('/api/nova_senha', methods=['POST'])
def nova_senha():
    try:
        dados = get_json_payload()
        token = normalize_spaces(dados.get('token'))
        senha_hash = generate_password_hash(validate_password(dados.get('senha')))
        email = serializer.loads(token, salt='recuperacao-senha', max_age=3600)
    except Exception:
        return json_error('O link de recuperacao e invalido, expirou ou a senha nao atende aos requisitos.', 400)

    conn = get_db_connection()
    conn.execute('UPDATE usuario SET senha = ? WHERE email = ?', (senha_hash, email))
    conn.commit()
    conn.close()
    return jsonify({'sucesso': True, 'mensagem': 'Sua senha foi alterada com sucesso! Faca login.'})


@app.route('/api/plantacao', methods=['POST'])
@login_required
def nova_plantacao():
    try:
        dados = get_json_payload()
        nome = validate_text(dados.get('nome'), 'Nome da plantacao', 2)
        area = validate_positive_float(dados.get('area'), 'Area')
        plantio = validate_date(dados.get('plantio'), 'Data de plantio')
        colheita = validate_date(dados.get('colheita'), 'Previsao de colheita')
        if colheita <= plantio:
            raise ValueError('A colheita deve ser posterior ao plantio.')
    except ValueError as exc:
        return json_error(str(exc))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO plantacao (nome, area, data_plantio, data_colheita, id_usuario) VALUES (?, ?, ?, ?, ?)',
        (nome, area, plantio, colheita, current_user_id()),
    )
    conn.commit()
    novo_id = cursor.lastrowid
    conn.close()
    return jsonify({'sucesso': True, 'id': novo_id})


@app.route('/api/plantacoes/<int:id_usuario>', methods=['GET'])
@login_required
def listar_plantacoes(id_usuario):
    if id_usuario != current_user_id():
        return json_error('Acesso negado.', 403)
    conn = get_db_connection()
    plantacoes = conn.execute('SELECT * FROM plantacao WHERE id_usuario = ?', (current_user_id(),)).fetchall()
    conn.close()
    return jsonify([dict(p) for p in plantacoes])


@app.route('/api/plantacao/<int:id_plantacao>', methods=['DELETE'])
@login_required
def deletar_plantacao(id_plantacao):
    conn = get_db_connection()
    try:
        usuario_id = current_user_id()

        cursor = conn.execute(
            'DELETE FROM insumo_uso WHERE id_plantacao = ? AND id_usuario = ?',
            (id_plantacao, usuario_id),
        )
        insumos_removidos = cursor.rowcount

        cursor = conn.execute(
            'DELETE FROM plantacao WHERE id = ? AND id_usuario = ?',
            (id_plantacao, usuario_id),
        )
        if cursor.rowcount == 0:
            conn.rollback()
            return json_error('Plantacao nao encontrada.', 404)

        conn.commit()
        return jsonify({
            'sucesso': True,
            'insumos_removidos': insumos_removidos,
        })
    except sqlite3.Error:
        conn.rollback()
        return json_error('Nao foi possivel apagar a plantacao.', 500)
    finally:
        conn.close()


@app.route('/api/financas', methods=['POST'])
@login_required
def add_financa():
    try:
        dados = get_json_payload()
        tipo = normalize_spaces(dados.get('tipo'))
        if tipo not in {'receita', 'gasto'}:
            raise ValueError('Tipo de financa invalido.')
        valor = validate_positive_float(dados.get('valor'), 'Valor')
    except ValueError as exc:
        return json_error(str(exc))

    conn = get_db_connection()
    conn.execute('INSERT INTO financas (tipo, valor, id_usuario) VALUES (?, ?, ?)', (tipo, valor, current_user_id()))
    conn.commit()
    conn.close()
    return jsonify({'sucesso': True})


@app.route('/api/financas/<int:id_usuario>', methods=['GET'])
@login_required
def get_financas(id_usuario):
    if id_usuario != current_user_id():
        return json_error('Acesso negado.', 403)
    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM financas WHERE id_usuario = ?', (current_user_id(),)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/api/insumo_estoque', methods=['POST'])
@login_required
def add_estoque():
    try:
        dados = get_json_payload()
        nome = validate_text(dados.get('nome'), 'Nome do insumo', 2)
        qtd = validate_positive_float(dados.get('qtd'), 'Quantidade')
        unidade = normalize_spaces(dados.get('unidade'))
        if unidade not in UNIDADES_INSUMO:
            raise ValueError('Unidade invalida.')
        registro = validate_text(dados.get('registro'), 'Numero de registro', 1, 40)
        validade_raw = validate_date(dados.get('validadeRaw'), 'Data de validade')
        validade = validate_br_date(dados.get('validade'), 'Data de validade formatada')
    except ValueError as exc:
        return json_error(str(exc))

    conn = get_db_connection()
    existente = conn.execute(
        'SELECT * FROM insumo_estoque WHERE registro = ? AND validadeRaw = ? AND id_usuario = ?',
        (registro, validade_raw, current_user_id()),
    ).fetchone()

    if existente:
        conn.execute('UPDATE insumo_estoque SET quantidade = quantidade + ? WHERE id = ?', (qtd, existente['id']))
    else:
        conn.execute(
            'INSERT INTO insumo_estoque (nome, quantidade, unidade, registro, validade, validadeRaw, id_usuario) '
            'VALUES (?, ?, ?, ?, ?, ?, ?)',
            (nome, qtd, unidade, registro, validade, validade_raw, current_user_id()),
        )
    conn.commit()
    conn.close()
    return jsonify({'sucesso': True})


@app.route('/api/insumo_estoque/busca/<int:id_usuario>', methods=['GET'])
@login_required
def buscar_lotes(id_usuario):
    if id_usuario != current_user_id():
        return json_error('Acesso negado.', 403)
    termo = normalize_spaces(request.args.get('q', ''))[:60].lower()
    conn = get_db_connection()
    lotes = conn.execute(
        '''SELECT * FROM insumo_estoque
           WHERE id_usuario = ? AND (LOWER(nome) LIKE ? OR LOWER(registro) LIKE ?)''',
        (current_user_id(), f'%{termo}%', f'%{termo}%'),
    ).fetchall()
    conn.close()
    return jsonify([dict(l) for l in lotes])


@app.route('/api/insumo_uso', methods=['POST'])
@login_required
def add_uso():
    try:
        dados = get_json_payload()
        lotes_usados = dados.get('lotes', [])
        if not isinstance(lotes_usados, list) or not lotes_usados:
            raise ValueError('Nenhum insumo selecionado.')
        id_plantacao = int(dados.get('id_plantacao'))
        data_uso = validate_br_date(dados.get('dataUso'), 'Data de uso')
    except (TypeError, ValueError) as exc:
        return json_error(str(exc))

    conn = get_db_connection()
    cursor = conn.cursor()
    plantacao = cursor.execute(
        'SELECT * FROM plantacao WHERE id = ? AND id_usuario = ?',
        (id_plantacao, current_user_id()),
    ).fetchone()
    if not plantacao:
        conn.close()
        return json_error('Plantacao nao encontrada.', 404)

    try:
        for lote in lotes_usados:
            id_estoque = int(lote.get('id'))
            qtd_usada = validate_positive_float(lote.get('qtdUsada'), 'Quantidade usada')

            insumo = cursor.execute(
                'SELECT * FROM insumo_estoque WHERE id = ? AND id_usuario = ?',
                (id_estoque, current_user_id()),
            ).fetchone()
            if not insumo:
                conn.rollback()
                conn.close()
                return json_error('Um dos insumos nao foi encontrado.', 404)
            if float(insumo['quantidade']) < qtd_usada:
                conn.rollback()
                conn.close()
                return json_error(f'Estoque insuficiente para {insumo["nome"]}.')

            nova_qtd = round(float(insumo['quantidade']) - qtd_usada, 2)
            if nova_qtd <= 0:
                cursor.execute('DELETE FROM insumo_estoque WHERE id = ?', (id_estoque,))
            else:
                cursor.execute('UPDATE insumo_estoque SET quantidade = ? WHERE id = ?', (nova_qtd, id_estoque))

            cursor.execute(
                'INSERT INTO insumo_uso (nome, quantidade_usada, unidade, local_nome, data_uso, id_usuario, id_plantacao) '
                'VALUES (?, ?, ?, ?, ?, ?, ?)',
                (insumo['nome'], qtd_usada, insumo['unidade'], plantacao['nome'], data_uso, current_user_id(), id_plantacao),
            )

        conn.commit()
        conn.close()
        return jsonify({'sucesso': True})
    except (TypeError, ValueError) as exc:
        conn.rollback()
        conn.close()
        return json_error(str(exc))


@app.route('/api/insumo_estoque/<int:id_insumo>', methods=['DELETE'])
@login_required
def deletar_insumo_estoque(id_insumo):
    conn = get_db_connection()
    conn.execute('DELETE FROM insumo_estoque WHERE id = ? AND id_usuario = ?', (id_insumo, current_user_id()))
    conn.commit()
    conn.close()
    return jsonify({'sucesso': True})


@app.route('/api/insumos/<int:id_usuario>', methods=['GET'])
@login_required
def get_insumos(id_usuario):
    if id_usuario != current_user_id():
        return json_error('Acesso negado.', 403)
    conn = get_db_connection()
    estoque = conn.execute('SELECT * FROM insumo_estoque WHERE id_usuario = ?', (current_user_id(),)).fetchall()
    em_uso = conn.execute('SELECT * FROM insumo_uso WHERE id_usuario = ?', (current_user_id(),)).fetchall()
    conn.close()
    return jsonify({'estoque': [dict(r) for r in estoque], 'em_uso': [dict(r) for r in em_uso]})


if __name__ == '__main__':
    app.run(debug=True)
