from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from datetime import datetime, date
import os
import calendar

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'financeiro.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Modelos do Banco de Dados
class Ciclo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    data_inicio = db.Column(db.Date, nullable=False)
    data_fim = db.Column(db.Date, nullable=False)
    orcamento = db.Column(db.Float, nullable=False)
    ativo = db.Column(db.Boolean, default=True)

class GastoFixo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    categoria = db.Column(db.String(50), nullable=False)
    forma_pgto = db.Column(db.String(10), nullable=False, default='Debito')  # Debito | Credito
    ciclo_id = db.Column(db.Integer, db.ForeignKey('ciclo.id'), nullable=False, index=True)

    
class Lancamento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False)
    descricao = db.Column(db.String(200), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    categoria = db.Column(db.String(50), nullable=False)
    forma_pgto = db.Column(db.String(10), nullable=False, default='Debito')  # Debito | Credito
    divida_id = db.Column(db.Integer, nullable=True)
    parcela_num = db.Column(db.Integer, nullable=True)
    ultima_parcela = db.Column(db.Integer, nullable=False, default=0)  # 0=normal | 1=pagamento do final

class Investimento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    tipo = db.Column(db.String(50), nullable=False)

class CartaoCredito(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    valor_atual = db.Column(db.Float, nullable=False)
    limite = db.Column(db.Float, nullable=False)
    data_vencimento = db.Column(db.Date, nullable=False)

class Divida(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)          # Ex: Financiamento Carro
    tipo = db.Column(db.String(50), nullable=False)           # Ex: Financiamento, Empréstimo
    saldo_inicial = db.Column(db.Float, nullable=False)
    saldo_atual = db.Column(db.Float, nullable=False)
    parcela_mensal = db.Column(db.Float, nullable=True)       # opcional
    taxa_mensal = db.Column(db.Float, nullable=True)          # % ao mês (opcional)
    data_inicio = db.Column(db.Date, nullable=True)
    data_fim_prevista = db.Column(db.Date, nullable=True)
    total_parcelas = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='Ativa')  # Ativa | Quitada


class ChecklistStatus(db.Model):
    __tablename__ = 'checklist_status'
    id = db.Column(db.Integer, primary_key=True)
    ciclo_id = db.Column(db.Integer, nullable=False)
    tipo = db.Column(db.String(20), nullable=False)   # fixed | transaction | card | debt
    ref_id = db.Column(db.Integer, nullable=False)
    checked = db.Column(db.Integer, nullable=False, default=0)  # 0=não pago | 1=pago
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('ciclo_id', 'tipo', 'ref_id', name='uq_checklist_item'),
    )


def _ciclo_para_data(data_lanc):
    """Retorna o ciclo que contém a data informada (ou None)."""
    return Ciclo.query.filter(Ciclo.data_inicio <= data_lanc, Ciclo.data_fim >= data_lanc).first()

def _add_months(dt, months: int):
    if dt is None:
        return None
    y = dt.year + (dt.month - 1 + months) // 12
    m = (dt.month - 1 + months) % 12 + 1
    last_day = calendar.monthrange(y, m)[1]
    d = min(dt.day, last_day)
    return dt.__class__(y, m, d)

# Rotas
@app.route('/')
def index():
    return render_template('index.html')

# API - Ciclo
@app.route('/api/ciclo', methods=['GET'])
def get_ciclo():
    ciclo = Ciclo.query.filter_by(ativo=True).first()
    if not ciclo:
        return jsonify({'error': 'Nenhum ciclo ativo'}), 404
    return jsonify({
        'id': ciclo.id,
        'nome': ciclo.nome,
        'data_inicio': ciclo.data_inicio.strftime('%Y-%m-%d'),
        'data_fim': ciclo.data_fim.strftime('%Y-%m-%d'),
        'orcamento': ciclo.orcamento
    })

@app.route('/api/ciclo', methods=['POST'])
def criar_ciclo():
    data = request.json

    ciclo_anterior = Ciclo.query.filter_by(ativo=True).first()  # <-- antes de desativar

    Ciclo.query.update({'ativo': False})

    novo_ciclo = Ciclo(
        nome=data['nome'],
        data_inicio=datetime.strptime(data['data_inicio'], '%Y-%m-%d').date(),
        data_fim=datetime.strptime(data['data_fim'], '%Y-%m-%d').date(),
        orcamento=float(data['orcamento']),
        ativo=True
    )
    db.session.add(novo_ciclo)
    db.session.commit()

    # COPIA fixos do ciclo anterior -> novo ciclo
    if ciclo_anterior:
        fixos_antigos = GastoFixo.query.filter_by(ciclo_id=ciclo_anterior.id).all()
        for f in fixos_antigos:
            db.session.add(GastoFixo(
                nome=f.nome,
                valor=f.valor,
                categoria=f.categoria,
                forma_pgto=getattr(f, 'forma_pgto', 'Debito'),
                ciclo_id=novo_ciclo.id
            ))
        db.session.commit()

    return jsonify({'message': 'Ciclo criado com sucesso', 'id': novo_ciclo.id}), 201

# API - Ciclos (listar/ativar/editar/deletar)
@app.route('/api/ciclos', methods=['GET'])
def listar_ciclos():
    ciclos = Ciclo.query.order_by(Ciclo.data_inicio.desc()).all()
    return jsonify([{
        'id': c.id,
        'nome': c.nome,
        'data_inicio': c.data_inicio.strftime('%Y-%m-%d'),
        'data_fim': c.data_fim.strftime('%Y-%m-%d'),
        'orcamento': c.orcamento,
        'ativo': c.ativo
    } for c in ciclos])

@app.route('/api/ciclos/<int:id>', methods=['PUT'])
def atualizar_ciclo(id):
    ciclo = Ciclo.query.get_or_404(id)
    data = request.json or {}
    if 'nome' in data:
        ciclo.nome = data['nome']
    if 'data_inicio' in data:
        ciclo.data_inicio = datetime.strptime(data['data_inicio'], '%Y-%m-%d').date()
    if 'data_fim' in data:
        ciclo.data_fim = datetime.strptime(data['data_fim'], '%Y-%m-%d').date()
    if 'orcamento' in data:
        ciclo.orcamento = float(data['orcamento'])
    db.session.commit()
    return jsonify({'message': 'Ciclo atualizado'}), 200

@app.route('/api/ciclos/<int:id>/ativar', methods=['POST'])
def ativar_ciclo(id):
    Ciclo.query.update({'ativo': False})
    ciclo = Ciclo.query.get_or_404(id)
    ciclo.ativo = True
    db.session.commit()
    return jsonify({'message': 'Ciclo ativado'}), 200

@app.route('/api/ciclos/<int:id>', methods=['DELETE'])
def deletar_ciclo(id):
    ciclo = Ciclo.query.get_or_404(id)
    db.session.delete(ciclo)
    db.session.commit()
    return jsonify({'message': 'Ciclo deletado'}), 200

# API - Gastos Fixos
@app.route('/api/gastos-fixos', methods=['GET'])
def get_gastos_fixos():
    ciclo_id = request.args.get('ciclo_id', type=int)

    # fallback seguro (não quebra se esquecer de mandar ciclo_id)
    if not ciclo_id:
        ciclo_ativo = Ciclo.query.filter_by(ativo=True).first()
        ciclo_id = ciclo_ativo.id if ciclo_ativo else None

    q = GastoFixo.query
    if ciclo_id:
        q = q.filter_by(ciclo_id=ciclo_id)

    gastos = q.order_by(GastoFixo.id.desc()).all()

    return jsonify([{
        'id': g.id,
        'nome': g.nome,
        'valor': g.valor,
        'categoria': g.categoria,
        'forma_pgto': getattr(g, 'forma_pgto', 'Debito'),
        'ciclo_id': g.ciclo_id
    } for g in gastos])

@app.route('/api/gastos-fixos', methods=['POST'])
def criar_gasto_fixo():
    data = request.json or {}

    ciclo_id = data.get('ciclo_id')
    if not ciclo_id:
        # fallback: se frontend esquecer, usa ciclo ativo
        ciclo_ativo = Ciclo.query.filter_by(ativo=True).first()
        if not ciclo_ativo:
            return jsonify({'error': 'Nenhum ciclo ativo e ciclo_id não informado'}), 400
        ciclo_id = ciclo_ativo.id

    novo_gasto = GastoFixo(
        nome=data['nome'],
        valor=float(data['valor']),
        categoria=data['categoria'],
        forma_pgto=data.get('forma_pgto', 'Debito'),
        ciclo_id=int(ciclo_id)
    )
    db.session.add(novo_gasto)
    db.session.commit()
    return jsonify({'message': 'Gasto fixo criado', 'id': novo_gasto.id}), 201


@app.route('/api/gastos-fixos/<int:id>', methods=['PUT'])
def atualizar_gasto_fixo(id):
    gasto = GastoFixo.query.get_or_404(id)
    data = request.json or {}

    gasto.nome = data.get('nome', gasto.nome)
    if 'valor' in data:
        gasto.valor = float(data['valor'])
    gasto.categoria = data.get('categoria', gasto.categoria)
    if 'forma_pgto' in data:
        gasto.forma_pgto = data.get('forma_pgto', gasto.forma_pgto)

    # NÃO permitir alterar ciclo_id aqui
    db.session.commit()
    return jsonify({'message': 'Gasto fixo atualizado'}), 200

@app.route('/api/gastos-fixos/<int:id>', methods=['DELETE'])
def deletar_gasto_fixo(id):
    gasto = GastoFixo.query.get_or_404(id)
    db.session.delete(gasto)
    db.session.commit()
    return jsonify({'message': 'Gasto fixo deletado'}), 200

# API - Lançamentos
@app.route('/api/lancamentos', methods=['GET'])
def get_lancamentos():
    ciclo_id = request.args.get('ciclo_id', type=int)
    query = Lancamento.query
    if ciclo_id:
        ciclo = Ciclo.query.get_or_404(ciclo_id)
        query = query.filter(Lancamento.data >= ciclo.data_inicio, Lancamento.data <= ciclo.data_fim)
    lancamentos = query.order_by(Lancamento.data.desc()).all()
    return jsonify([{
        'id': l.id,
        'data': l.data.strftime('%Y-%m-%d'),
        'descricao': l.descricao,
        'valor': l.valor,
        'categoria': l.categoria,
        'forma_pgto': getattr(l, 'forma_pgto', 'Debito'),

        # ✅ NOVOS (pra não “sumir” ao editar)
        'divida_id': getattr(l, 'divida_id', None),
        'parcela_num': getattr(l, 'parcela_num', None),
        'ultima_parcela': int(getattr(l, 'ultima_parcela', 0) or 0)
    } for l in lancamentos])

@app.route('/api/lancamentos', methods=['POST'])
def criar_lancamento():
    data = request.json or {}
    data_lanc = datetime.strptime(data['data'], '%Y-%m-%d').date()

    # Retroativo/histórico: garante que existe um ciclo que cobre esta data
    ciclo = _ciclo_para_data(data_lanc)
    if not ciclo:
        return jsonify({
            'error': 'Nenhum ciclo cobre esta data',
            'detail': 'Crie um ciclo que inclua essa data (Configurar Ciclo) ou ajuste a data do lançamento.'
        }), 400

    divida_id = data.get('divida_id')
    parcela_num = data.get('parcela_num')

    if divida_id not in (None, '', 0, '0'):
        if parcela_num in (None, '', 0, '0'):
            return jsonify({'error': 'Informe a parcela paga para a dívida selecionada.'}), 400

    novo_lancamento = Lancamento(
        data=data_lanc,
        descricao=data['descricao'],
        valor=float(data['valor']),
        categoria=data['categoria'],
        forma_pgto=data.get('forma_pgto', 'Debito'),
        divida_id=int(divida_id) if divida_id not in (None, '', 0, '0') else None,
        parcela_num=int(parcela_num) if parcela_num not in (None, '', 0, '0') else None,
        ultima_parcela=1 if str(data.get('ultima_parcela', 0)).lower() in ('1','true','yes','on') else 0
    )

    db.session.add(novo_lancamento)
    db.session.commit()
    return jsonify({'message': 'Lançamento criado', 'id': novo_lancamento.id}), 201

@app.route('/api/lancamentos/<int:id>', methods=['PUT'])
def atualizar_lancamento(id):
    lancamento = Lancamento.query.get_or_404(id)
    data = request.json or {}

    if 'data' in data and data['data']:
        nova_data = datetime.strptime(data['data'], '%Y-%m-%d').date()
        ciclo = _ciclo_para_data(nova_data)
        if not ciclo:
            return jsonify({
                'error': 'Nenhum ciclo cobre esta data',
                'detail': 'Crie um ciclo que inclua essa data (Configurar Ciclo) ou ajuste a data do lançamento.'
            }), 400
        lancamento.data = nova_data

    lancamento.descricao = data.get('descricao', lancamento.descricao)
    if 'valor' in data:
        lancamento.valor = float(data['valor'])
    lancamento.categoria = data.get('categoria', lancamento.categoria)

    if 'forma_pgto' in data and data.get('forma_pgto'):
        lancamento.forma_pgto = data.get('forma_pgto')

    if 'divida_id' in data:
        divida_id = data.get('divida_id')
        lancamento.divida_id = int(divida_id) if divida_id not in (None, '', 0, '0') else None

    if 'parcela_num' in data:
        parcela_num = data.get('parcela_num')
        lancamento.parcela_num = int(parcela_num) if parcela_num not in (None, '', 0, '0') else None

    if 'ultima_parcela' in data:
        lancamento.ultima_parcela = 1 if str(data.get('ultima_parcela')).lower() in ('1','true','yes','on') else 0

    # Se removi o vínculo com dívida, limpa parcela/flag
    if lancamento.divida_id is None:
        lancamento.parcela_num = None
        lancamento.ultima_parcela = 0

    # Se ficou vinculado a uma dívida, precisa ter parcela
    if lancamento.divida_id is not None and lancamento.parcela_num is None:
        return jsonify({'error': 'Informe a parcela paga para a dívida selecionada.'}), 400

    db.session.commit()
    return jsonify({'message': 'Lançamento atualizado'}), 200

@app.route('/api/lancamentos/<int:id>', methods=['DELETE'])

def deletar_lancamento(id):
    lancamento = Lancamento.query.get_or_404(id)
    db.session.delete(lancamento)
    db.session.commit()
    return jsonify({'message': 'Lançamento deletado'}), 200

# API - Investimentos
@app.route('/api/investimentos', methods=['GET'])
def get_investimentos():
    investimentos = Investimento.query.all()
    return jsonify([{
        'id': i.id,
        'nome': i.nome,
        'valor': i.valor,
        'tipo': i.tipo
    } for i in investimentos])

@app.route('/api/investimentos', methods=['POST'])
def criar_investimento():
    data = request.json
    novo_investimento = Investimento(
        nome=data['nome'],
        valor=float(data['valor']),
        tipo=data['tipo']
    )
    db.session.add(novo_investimento)
    db.session.commit()
    return jsonify({'message': 'Investimento criado', 'id': novo_investimento.id}), 201

@app.route('/api/investimentos/<int:id>', methods=['PUT'])
def atualizar_investimento(id):
    investimento = Investimento.query.get_or_404(id)
    data = request.json or {}
    investimento.nome = data.get('nome', investimento.nome)
    if 'valor' in data:
        investimento.valor = float(data['valor'])
    investimento.tipo = data.get('tipo', investimento.tipo)
    db.session.commit()
    return jsonify({'message': 'Investimento atualizado'}), 200

@app.route('/api/investimentos/<int:id>', methods=['DELETE'])
def deletar_investimento(id):
    investimento = Investimento.query.get_or_404(id)
    db.session.delete(investimento)
    db.session.commit()
    return jsonify({'message': 'Investimento deletado'}), 200

# API - Cartões de Crédito
@app.route('/api/cartoes', methods=['GET'])
def get_cartoes():
    cartoes = CartaoCredito.query.all()
    return jsonify([{
        'id': c.id,
        'nome': c.nome,
        'valor_atual': c.valor_atual,
        'limite': c.limite,
        'data_vencimento': c.data_vencimento.strftime('%Y-%m-%d')
    } for c in cartoes])

@app.route('/api/cartoes', methods=['POST'])
def criar_cartao():
    data = request.json
    novo_cartao = CartaoCredito(
        nome=data['nome'],
        valor_atual=float(data['valor_atual']),
        limite=float(data['limite']),
        data_vencimento=datetime.strptime(data['data_vencimento'], '%Y-%m-%d').date()
    )
    db.session.add(novo_cartao)
    db.session.commit()
    return jsonify({'message': 'Cartão criado', 'id': novo_cartao.id}), 201

@app.route('/api/cartoes/<int:id>', methods=['PUT'])
def atualizar_cartao(id):
    cartao = CartaoCredito.query.get_or_404(id)
    data = request.json or {}
    cartao.nome = data.get('nome', cartao.nome)
    if 'valor_atual' in data:
        cartao.valor_atual = float(data['valor_atual'])
    if 'limite' in data:
        cartao.limite = float(data['limite'])
    if 'data_vencimento' in data:
        cartao.data_vencimento = datetime.strptime(data['data_vencimento'], '%Y-%m-%d').date()
    db.session.commit()
    return jsonify({'message': 'Cartão atualizado'}), 200

@app.route('/api/cartoes/<int:id>', methods=['DELETE'])
def deletar_cartao(id):
    cartao = CartaoCredito.query.get_or_404(id)
    db.session.delete(cartao)
    db.session.commit()
    return jsonify({'message': 'Cartão deletado'}), 200


# API - Dívidas
@app.route('/api/dividas', methods=['GET'])
def get_dividas():
    dividas = Divida.query.order_by(Divida.id.desc()).all()
    out = []
    for d in dividas:
        rows = (Lancamento.query
                .filter(Lancamento.divida_id == d.id)
                .with_entities(Lancamento.parcela_num, getattr(Lancamento, 'ultima_parcela', 0))
                .all())

        forward_nums = [int(p) for (p, u) in rows if p is not None and int(u or 0) == 0]
        end_nums = [int(p) for (p, u) in rows if p is not None and int(u or 0) == 1]

        forward_set = set(forward_nums)
        end_set = set(end_nums)

        total = getattr(d, 'total_parcelas', None)
        total_i = int(total) if total not in (None, '') else None

        # parcela_atual: maior parcela informada no fluxo normal (frente)
        parcela_atual = max(forward_nums) if forward_nums else 0

        # antecipações do final reduzem o total efetivo
        total_ajustado = (total_i - len(end_set)) if total_i is not None else None
        
        # Fim previsto ajustado (dinâmico): data_inicio + (total_ajustado - 1) meses
        fim_prev_ajustada = None
        if d.data_inicio and total_ajustado is not None:
            fim_prev_ajustada = _add_months(d.data_inicio, max(total_ajustado - 1, 0))

        faltam = (total_ajustado - parcela_atual) if total_ajustado is not None else None
        proxima = None
        if total_ajustado is not None:
            proxima = min(parcela_atual + 1, total_ajustado) if parcela_atual < total_ajustado else total_ajustado

        fim_contratual_ajustada = None
        if d.data_inicio and total_ajustado is not None:
            fim_contratual_ajustada = _add_months(d.data_inicio, max(int(total_ajustado) - 1, 0))

        base_ref = None
        last_dt = (Lancamento.query
                .filter(Lancamento.divida_id == d.id)
                .with_entities(Lancamento.data)
                .order_by(Lancamento.data.desc())
                .first())
        base_ref = last_dt[0] if last_dt and last_dt[0] else None
        if not base_ref:
            base_ref = date.today()

        fim_estimado_atual = None
        if faltam is not None:
            fim_estimado_atual = _add_months(base_ref, max(int(faltam) - 1, 0))


        out.append({
            'id': d.id,
            'nome': d.nome,
            'tipo': d.tipo,
            'saldo_inicial': d.saldo_inicial,
            'saldo_atual': d.saldo_atual,
            'parcela_mensal': d.parcela_mensal,
            'taxa_mensal': d.taxa_mensal,
            'data_inicio': d.data_inicio.strftime('%Y-%m-%d') if d.data_inicio else None,
            'data_fim_estimado_atual': fim_estimado_atual.strftime('%Y-%m-15') if fim_estimado_atual else None,

            'status': d.status,

            # original (para edição)
            'total_parcelas': total_i,
            # exibição (considera antecipações do final)
            'total_parcelas_ajustada': total_ajustado,

            'parcela_atual': parcela_atual,
            'faltam': faltam,
            'proxima_parcela': proxima,

            'parcelas_registradas': len(forward_set) + len(end_set),
            'antecipadas_final': len(end_set)
        })
    return jsonify(out)

@app.route('/api/dividas', methods=['POST'])

def criar_divida():
    data = request.json or {}
    nova = Divida(
        nome=data['nome'],
        tipo=data.get('tipo', 'Outro'),
        saldo_inicial=float(data.get('saldo_inicial', data.get('saldo_atual', 0) or 0)),
        saldo_atual=float(data.get('saldo_atual', data.get('saldo_inicial', 0) or 0)),
        parcela_mensal=float(data['parcela_mensal']) if data.get('parcela_mensal') not in (None, '') else None,
        taxa_mensal=float(data['taxa_mensal']) if data.get('taxa_mensal') not in (None, '') else None,
        data_inicio=datetime.strptime(data['data_inicio'], '%Y-%m-%d').date() if data.get('data_inicio') else None,
        data_fim_prevista=datetime.strptime(data['data_fim_prevista'], '%Y-%m-%d').date() if data.get('data_fim_prevista') else None,
        total_parcelas=int(data['total_parcelas']) if data.get('total_parcelas') not in (None,'') else None,
        status=data.get('status', 'Ativa')
    )
    db.session.add(nova)
    db.session.commit()
    return jsonify({'message': 'Dívida criada', 'id': nova.id}), 201

@app.route('/api/dividas/<int:id>', methods=['PUT'])
def atualizar_divida(id):
    d = Divida.query.get_or_404(id)
    data = request.json or {}
    d.nome = data.get('nome', d.nome)
    d.tipo = data.get('tipo', d.tipo)
    if 'saldo_inicial' in data and data['saldo_inicial'] not in (None, ''):
        d.saldo_inicial = float(data['saldo_inicial'])
    if 'saldo_atual' in data and data['saldo_atual'] not in (None, ''):
        d.saldo_atual = float(data['saldo_atual'])
    if 'parcela_mensal' in data:
        d.parcela_mensal = float(data['parcela_mensal']) if data['parcela_mensal'] not in (None, '') else None
    if 'taxa_mensal' in data:
        d.taxa_mensal = float(data['taxa_mensal']) if data['taxa_mensal'] not in (None, '') else None
    if 'data_inicio' in data:
        d.data_inicio = datetime.strptime(data['data_inicio'], '%Y-%m-%d').date() if data['data_inicio'] else None
    if 'data_fim_prevista' in data:
        d.data_fim_prevista = datetime.strptime(data['data_fim_prevista'], '%Y-%m-%d').date() if data['data_fim_prevista'] else None
    if 'total_parcelas' in data:
        d.total_parcelas = int(data['total_parcelas']) if data['total_parcelas'] not in (None,'') else None
    if 'status' in data:
        d.status = data['status']
    db.session.commit()
    return jsonify({'message': 'Dívida atualizada'}), 200

@app.route('/api/dividas/<int:id>', methods=['DELETE'])
def deletar_divida(id):
    d = Divida.query.get_or_404(id)
    db.session.delete(d)
    db.session.commit()
    return jsonify({'message': 'Dívida deletada'}), 200

# API - Checklist de Pagamentos (por ciclo)
@app.route('/api/checklist', methods=['GET'])
def get_checklist():
    ciclo_id = request.args.get('ciclo_id', type=int)
    if not ciclo_id:
        return jsonify({'error': 'ciclo_id é obrigatório'}), 400

    ciclo = Ciclo.query.get_or_404(ciclo_id)

    # Estados salvos no banco (por ciclo)
    rows = (ChecklistStatus.query
            .filter(ChecklistStatus.ciclo_id == ciclo_id)
            .with_entities(ChecklistStatus.tipo, ChecklistStatus.ref_id, ChecklistStatus.checked)
            .all())
    state = {(t, int(r)): int(ch or 0) for (t, r, ch) in rows}

    # Itens do ciclo
    fixos = (GastoFixo.query
         .filter(GastoFixo.ciclo_id == ciclo_id)
         .filter(GastoFixo.forma_pgto == 'Debito')
         .order_by(GastoFixo.nome.asc())
         .all())

    lancs = (Lancamento.query
             .filter(Lancamento.data >= ciclo.data_inicio, Lancamento.data <= ciclo.data_fim)
             .filter(Lancamento.forma_pgto == 'Debito')
             .order_by(Lancamento.data.asc(), Lancamento.descricao.asc())
             .all())
    cartoes = CartaoCredito.query.order_by(CartaoCredito.nome.asc()).all()
    dividas = Divida.query.order_by(Divida.nome.asc()).all()

    def item(tipo, ref_id, titulo, subtitulo, valor):
        return {
            'tipo': tipo,
            'ref_id': ref_id,
            'titulo': titulo,
            'subtitulo': subtitulo,
            'valor': float(valor) if valor is not None else None,
            'checked': state.get((tipo, int(ref_id)), 0)
        }

    return jsonify({
        'ciclo_id': ciclo_id,
        'fixos': [item('fixed', g.id, g.nome, 'Fixos (Débito/Pix)', g.valor) for g in fixos],
        'lancamentos': [item('transaction', l.id, l.descricao, f"Lançamentos (Débito/Pix) • {l.data.strftime('%d/%m/%Y')}", l.valor) for l in lancs],
        'cartoes': [item('card', c.id, f"Fatura {c.nome}", 'Cartões', c.valor_atual) for c in cartoes],
        'dividas': [item('debt', d.id, d.nome, 'Dívidas', d.parcela_mensal if d.parcela_mensal is not None else None) for d in dividas],
    })


@app.route('/api/checklist', methods=['PUT'])
def upsert_checklist():
    data = request.json or {}
    ciclo_id = int(data.get('ciclo_id') or 0)
    tipo = (data.get('tipo') or '').strip()
    ref_id = int(data.get('ref_id') or 0)
    checked = 1 if int(data.get('checked') or 0) == 1 else 0

    if not ciclo_id or not tipo or not ref_id:
        return jsonify({'error': 'ciclo_id, tipo e ref_id são obrigatórios'}), 400

    row = (ChecklistStatus.query
           .filter_by(ciclo_id=ciclo_id, tipo=tipo, ref_id=ref_id)
           .first())
    if not row:
        row = ChecklistStatus(ciclo_id=ciclo_id, tipo=tipo, ref_id=ref_id, checked=checked)
        db.session.add(row)
    else:
        row.checked = checked
        row.updated_at = datetime.utcnow()

    db.session.commit()
    return jsonify({'message': 'Checklist atualizado'}), 200





# Inicializar banco de dados
def init_db():
    with app.app_context():
        db.create_all()

        # Migração leve (SQLite): colunas novas para vincular lançamentos a dívidas
        try:
            cols_l = [row[1] for row in db.session.execute(text("PRAGMA table_info(lancamento)")).fetchall()]
            if 'divida_id' not in cols_l:
                db.session.execute(text("ALTER TABLE lancamento ADD COLUMN divida_id INTEGER"))
            if 'parcela_num' not in cols_l:
                db.session.execute(text("ALTER TABLE lancamento ADD COLUMN parcela_num INTEGER"))
            if 'ultima_parcela' not in cols_l:
                db.session.execute(text("ALTER TABLE lancamento ADD COLUMN ultima_parcela INTEGER NOT NULL DEFAULT 0"))
            if 'forma_pgto' not in cols_l:
                db.session.execute(text("ALTER TABLE lancamento ADD COLUMN forma_pgto VARCHAR(10) NOT NULL DEFAULT 'Debito'"))
            db.session.commit()
        except Exception as e:
            print("Aviso migração lancamento:", e)

        try:
            cols_d = [row[1] for row in db.session.execute(text("PRAGMA table_info(divida)")).fetchall()]
            if 'total_parcelas' not in cols_d:
                db.session.execute(text("ALTER TABLE divida ADD COLUMN total_parcelas INTEGER"))
                db.session.commit()
        except Exception as e:
            print("Aviso migração divida:", e)

        
        # Migração leve (SQLite): adiciona coluna forma_pgto em gasto_fixo se não existir
        try:
            cols = [row[1] for row in db.session.execute(db.text("PRAGMA table_info(gasto_fixo)")).fetchall()]
            if 'forma_pgto' not in cols:
                db.session.execute(
                    db.text("ALTER TABLE gasto_fixo ADD COLUMN forma_pgto VARCHAR(10) NOT NULL DEFAULT 'Debito'")
                )
                db.session.commit()
        except Exception as e:
            print("Aviso migração gasto_fixo:", e)
            
        # Migração leve (SQLite): adiciona coluna forma_pgto em lancamento se não existir
        try:
            cols_l = [row[1] for row in db.session.execute(db.text("PRAGMA table_info(lancamento)")).fetchall()]
            if 'forma_pgto' not in cols_l:
                db.session.execute(
                    db.text("ALTER TABLE lancamento ADD COLUMN forma_pgto VARCHAR(10) NOT NULL DEFAULT 'Debito'")
                )
                db.session.commit()
        except Exception as e:
            print("Aviso migração lancamento:", e)

        # Migração leve (SQLite): adiciona coluna forma_pgto em lancamento se não existir
        try:
            cols_l = [row[1] for row in db.session.execute(db.text("PRAGMA table_info(lancamento)")).fetchall()]
            if 'forma_pgto' not in cols_l:
                db.session.execute(
                    db.text("ALTER TABLE lancamento ADD COLUMN forma_pgto VARCHAR(10) NOT NULL DEFAULT 'Debito'")
                )
                db.session.commit()
        except Exception as e:
            print("Aviso migração lancamento:", e)
            
        # Migração leve (SQLite): adiciona coluna ciclo_id em gasto_fixo se não existir + backfill
        try:
            cols_gf = [row[1] for row in db.session.execute(text("PRAGMA table_info(gasto_fixo)")).fetchall()]

            if 'ciclo_id' not in cols_gf:
                db.session.execute(text("ALTER TABLE gasto_fixo ADD COLUMN ciclo_id INTEGER"))
                db.session.commit()

            # Backfill: define ciclo_id para registros antigos que ficaram NULL
            ciclo_ativo = Ciclo.query.filter_by(ativo=True).first()
            if ciclo_ativo:
                db.session.execute(
                    text("UPDATE gasto_fixo SET ciclo_id = :cid WHERE ciclo_id IS NULL"),
                    {"cid": ciclo_ativo.id}
                )
                db.session.commit()

        except Exception as e:
            print("Aviso migração ciclo_id gasto_fixo:", e)
            

        # Verificar se já existe um ciclo ativo
        if not Ciclo.query.filter_by(ativo=True).first():
            # Criar ciclo padrão
            ciclo_padrao = Ciclo(
                nome='Janeiro 2026',
                data_inicio=datetime(2026, 1, 1).date(),
                data_fim=datetime(2026, 1, 31).date(),
                orcamento=5000.00,
                ativo=True
            )
            
            db.session.add(ciclo_padrao)
            db.session.commit()  # precisa do id do ciclo para os fixos

            gastos_exemplo = [
                GastoFixo(nome='Netflix', valor=45.90, categoria='Assinatura', forma_pgto='Debito', ciclo_id=ciclo_padrao.id),
                GastoFixo(nome='Água', valor=80.00, categoria='Utilidades', forma_pgto='Debito', ciclo_id=ciclo_padrao.id),
                GastoFixo(nome='Luz', valor=150.00, categoria='Utilidades', forma_pgto='Debito', ciclo_id=ciclo_padrao.id)
            ]


            lancamentos_exemplo = [
                Lancamento(data=datetime(2026, 1, 5).date(), descricao='Supermercado', valor=250.00, categoria='Alimentação'),
                Lancamento(data=datetime(2026, 1, 10).date(), descricao='Gasolina', valor=200.00, categoria='Transporte')
            ]
            
            investimentos_exemplo = [
                Investimento(nome='Tesouro Direto', valor=500.00, tipo='Renda Fixa'),
                Investimento(nome='Ações', valor=1000.00, tipo='Renda Variável')
            ]
            
            cartoes_exemplo = [
                CartaoCredito(nome='Nubank', valor_atual=450.00, limite=3000.00, data_vencimento=datetime(2026, 1, 15).date())
            ]
            
            for item in gastos_exemplo + lancamentos_exemplo + investimentos_exemplo + cartoes_exemplo:
                db.session.add(item)
            
            db.session.commit()
            print("Banco de dados inicializado com dados de exemplo!")

if __name__ == '__main__':
    init_db()
    print("Sistema iniciado! Acesse: http://127.0.0.1:5000")
    app.run(debug=True)