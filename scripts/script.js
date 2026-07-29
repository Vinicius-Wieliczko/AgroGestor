// ==========================================
// FUNÇÕES AUXILIARES GERAIS
// ==========================================
window.limitDecimals = function(e) {
    if(e.value.includes('.')) {
        let parts = e.value.split('.');
        if(parts[1].length > 2) e.value = parts[0] + '.' + parts[1].substring(0, 2);
    }
};

function formatDate(dateStr) {
    if(!dateStr) return '--/--/----';
    return dateStr.split('-').reverse().join('/');
}

function validarCPF(cpf) {
    cpf = cpf.replace(/[^\d]+/g, '');
    if (cpf.length !== 11 || /^(\d)\1+$/.test(cpf)) return false;
    let soma = 0, resto;
    for (let i = 1; i <= 9; i++) soma += parseInt(cpf.substring(i - 1, i)) * (11 - i);
    resto = (soma * 10) % 11;
    if (resto === 10 || resto === 11) resto = 0;
    if (resto !== parseInt(cpf.substring(9, 10))) return false;
    soma = 0;
    for (let i = 1; i <= 10; i++) soma += parseInt(cpf.substring(i - 1, i)) * (12 - i);
    resto = (soma * 10) % 11;
    if (resto === 10 || resto === 11) resto = 0;
    if (resto !== parseInt(cpf.substring(10, 11))) return false;
    return true;
}

// ==========================================
// 1. AUTENTICAÇÃO E INICIALIZAÇÃO
// ==========================================
let usuarioLogado = null; 

const urlParams = new URLSearchParams(window.location.search);
const tokenRecuperacao = urlParams.get('token');

if (tokenRecuperacao) {
    document.getElementById('login-screen').style.display = 'none';
    document.getElementById('reset-password-screen').style.display = 'flex';
    window.history.replaceState({}, document.title, "/");
}

document.getElementById('link-ir-cadastro').addEventListener('click', () => { document.getElementById('login-screen').style.display = 'none'; document.getElementById('register-screen').style.display = 'flex'; });
document.getElementById('link-ir-login').addEventListener('click', () => { document.getElementById('register-screen').style.display = 'none'; document.getElementById('login-screen').style.display = 'flex'; });
document.getElementById('link-esqueci-senha').addEventListener('click', () => { document.getElementById('login-screen').style.display = 'none'; document.getElementById('forgot-password-screen').style.display = 'flex'; });
document.getElementById('link-voltar-login').addEventListener('click', () => { document.getElementById('forgot-password-screen').style.display = 'none'; document.getElementById('login-screen').style.display = 'flex'; });
document.getElementById('link-voltar-login-reset')?.addEventListener('click', () => { document.getElementById('reset-password-screen').style.display = 'none'; document.getElementById('login-screen').style.display = 'flex'; });

document.getElementById('btn-fazer-cadastro').addEventListener('click', async () => {
    const nome = document.getElementById('cad-nome').value;
    const email = document.getElementById('cad-email').value;
    const cpf = document.getElementById('cad-cpf').value;
    const senha = document.getElementById('cad-senha').value;
    const confSenha = document.getElementById('cad-conf-senha').value;
    const estado = document.getElementById('cad-estado').value;

    if (!nome || !email || !cpf || !senha || !estado) { alert("Preencha todos os campos!"); return; }
    if (!validarCPF(cpf)) { alert("CPF Inválido! Verifique a numeração."); return; }
    if (senha !== confSenha) { alert("As senhas não coincidem!"); return; }

    const dados = { nome, email, cpf, senha, estado };
    try {
        const resposta = await fetch('/api/cadastro', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(dados) });
        const resultado = await resposta.json();
        alert(resultado.mensagem);
        if(resultado.sucesso) document.getElementById('link-ir-login').click();
    } catch(e) { alert("Erro de conexão. Servidor online?"); }
});

document.getElementById('btn-fazer-login').addEventListener('click', async () => {
    const email = document.getElementById('login-email').value;
    const senha = document.getElementById('login-senha').value;
    try {
        const resposta = await fetch('/api/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email, senha }) });
        const resultado = await resposta.json();

        if (resultado.sucesso) {
            usuarioLogado = resultado.usuario; 
            document.getElementById('auth-container').style.display = 'none';
            document.getElementById('app-container').style.display = 'block';
            
            initWeather(); 
            
            try { await carregarFinancasDoBanco(); } catch(e) { console.error("Erro Finanças", e); }
            try { await carregarInsumosDoBanco(); } catch(e) { console.error("Erro Insumos", e); }
            try { await carregarPlantacoesDoBanco(); } catch(e) { console.error("Erro Plantações", e); }
            
        } else { alert(resultado.mensagem); }
    } catch(e) { alert("Erro de conexão com servidor. Reinicie o Python."); }
});

document.getElementById('btn-enviar-recuperacao').addEventListener('click', async () => {
    const email = document.getElementById('recupera-email').value;
    const cpf = document.getElementById('recupera-cpf').value;
    
    if(!email || !cpf) { alert("Digite o e-mail e confirme seu CPF."); return; }
    if(!validarCPF(cpf)) { alert("CPF Inválido! Verifique a numeração."); return; }

    const btn = document.getElementById('btn-enviar-recuperacao');
    btn.textContent = "Enviando, aguarde...";
    btn.disabled = true;

    try {
        const resposta = await fetch('/api/recuperar_senha', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: email, cpf: cpf })
        });
        const resultado = await resposta.json();
        
        alert(resultado.mensagem);
        if(resultado.sucesso) {
            document.getElementById('link-voltar-login').click(); 
            document.getElementById('recupera-email').value = ''; 
            document.getElementById('recupera-cpf').value = ''; 
        }
    } catch(e) { alert("Erro ao conectar com o servidor."); }
    
    btn.textContent = "Enviar E-mail";
    btn.disabled = false;
});

document.getElementById('btn-salvar-nova-senha')?.addEventListener('click', async () => {
    const senha = document.getElementById('reset-senha').value;
    const confSenha = document.getElementById('reset-conf-senha').value;

    if (!senha || senha !== confSenha) { alert("As senhas não coincidem ou estão vazias!"); return; }

    try {
        const resposta = await fetch('/api/nova_senha', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token: tokenRecuperacao, senha: senha })
        });
        const resultado = await resposta.json();
        alert(resultado.mensagem);

        if (resultado.sucesso) {
            document.getElementById('reset-password-screen').style.display = 'none';
            document.getElementById('login-screen').style.display = 'flex';
        }
    } catch(e) { alert("Erro ao conectar com o servidor."); }
});

document.getElementById('btn-abrir-perfil').addEventListener('click', () => {
    if(usuarioLogado) {
        document.getElementById('perfil-nome').value = usuarioLogado.nome_completo;
        document.getElementById('perfil-email').value = usuarioLogado.email;
        document.getElementById('perfil-estado').value = usuarioLogado.estado;
    }
    openModal('modal-perfil');
});

document.getElementById('btn-salvar-perfil').addEventListener('click', async () => {
    const novoNome = document.getElementById('perfil-nome').value;
    const novoEstado = document.getElementById('perfil-estado').value;
    
    if(!novoNome) { alert("O nome não pode ficar vazio!"); return; }

    try {
        const resposta = await fetch(`/api/perfil/${usuarioLogado.id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ nome: novoNome, estado: novoEstado })
        });
        const resultado = await resposta.json();

        if(resultado.sucesso) {
            usuarioLogado.nome_completo = novoNome;
            usuarioLogado.estado = novoEstado;
            alert(resultado.mensagem);
            closeModal();
        } else { alert(resultado.mensagem); }
    } catch(e) { alert("Erro de comunicação com o servidor."); }
});

document.getElementById('btn-logout').addEventListener('click', () => {
    usuarioLogado = null; plantacoes = []; estoque = []; emUso = [];
    totalRecebido = 0; totalGasto = 0;
    updateFinanceUI(); 
    closeModal();
    document.getElementById('app-container').style.display = 'none';
    document.getElementById('auth-container').style.display = 'flex';
    document.getElementById('login-email').value = ''; document.getElementById('login-senha').value = '';
});

// ==========================================
// 2. PREVISÃO DO TEMPO 24H (COM ÍCONES DINÂMICOS)
// ==========================================

function obterIconeClima(codigoWMO, isDay) {
    if (codigoWMO === 0) return isDay ? '☀️' : '🌙'; 
    if (codigoWMO === 1 || codigoWMO === 2) return '⛅'; 
    if (codigoWMO === 3) return '☁️'; 
    if (codigoWMO === 45 || codigoWMO === 48) return '🌫️'; 
    if (codigoWMO >= 51 && codigoWMO <= 57) return '🌦️'; 
    if (codigoWMO >= 61 && codigoWMO <= 67) return '🌧️'; 
    if (codigoWMO >= 71 && codigoWMO <= 77) return '❄️'; 
    if (codigoWMO >= 80 && codigoWMO <= 82) return '🌦️'; 
    if (codigoWMO >= 95 && codigoWMO <= 99) return '⛈️'; 
    return isDay ? '☀️' : '🌙'; 
}

function initWeather() {
    const forecastContainer = document.getElementById('forecast-container');
    const weatherInfo = document.getElementById('weather-info');

    if ("geolocation" in navigator) {
        navigator.geolocation.getCurrentPosition(
            async (position) => {
                try {
                    const lat = position.coords.latitude;
                    const lon = position.coords.longitude;
                    const response = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current_weather=true&hourly=temperature_2m,weathercode&timezone=auto`);
                    const data = await response.json();
                    
                    const tempAtual = Math.round(data.current_weather.temperature);
                    const isDay = data.current_weather.is_day;
                    const codigoAtual = data.current_weather.weathercode;
                    
                    const iconeAtual = obterIconeClima(codigoAtual, isDay);

                    weatherInfo.innerHTML = `<div class="current-weather"><span class="icon">${iconeAtual}</span><span class="temp">${tempAtual}°C</span></div>`;
                    let forecastHTML = '';
                    
                    const agora = new Date();
                    const ano = agora.getFullYear(); const mes = String(agora.getMonth() + 1).padStart(2, '0');
                    const dia = String(agora.getDate()).padStart(2, '0'); const proximaHora = String(agora.getHours() + 1).padStart(2, '0'); 
                    const matchString = `${ano}-${mes}-${dia}T${proximaHora}:00`;
                    
                    let startIndex = data.hourly.time.findIndex(t => t === matchString);
                    if(startIndex === -1) startIndex = 0;

                    for(let i = 0; i < 24; i++) {
                        if (startIndex + i >= data.hourly.time.length) break;
                        
                        let horaData = new Date(data.hourly.time[startIndex + i]);
                        let h = horaData.getHours().toString().padStart(2, '0');
                        let temp = Math.round(data.hourly.temperature_2m[startIndex + i]);
                        
                        let codHora = data.hourly.weathercode[startIndex + i];
                        let isDayHora = (h >= 6 && h <= 18); 
                        let iconeHora = obterIconeClima(codHora, isDayHora);

                        forecastHTML += `<div class="forecast-item"><span>${h}:00</span><span>${iconeHora} ${temp}°C</span></div>`;
                    }
                    forecastContainer.innerHTML = forecastHTML;
                } catch (error) { weatherInfo.innerHTML = '<span class="empty-msg">Erro ao buscar clima.</span>'; }
            },
            () => { weatherInfo.innerHTML = '<span class="empty-msg">Localização negada.</span>'; }
        );
    }
}

// ==========================================
// 3. CONTROLE DE MODAIS GERAIS
// ==========================================
const modalOverlay = document.getElementById('modal-overlay');
function openModal(modalId) {
    document.querySelectorAll('.modal-content').forEach(m => m.style.display = 'none');
    modalOverlay.style.display = 'flex';
    document.getElementById(modalId).style.display = 'flex';
}
function closeModal() {
    modalOverlay.style.display = 'none';
    document.querySelectorAll('.modal-content').forEach(m => m.style.display = 'none');
}
document.querySelectorAll('.btn-back').forEach(btn => btn.addEventListener('click', closeModal));

// ==========================================
// 4. LÓGICA DE FINANÇAS
// ==========================================
let totalRecebido = 0;
let totalGasto = 0;

async function carregarFinancasDoBanco() {
    const res = await fetch(`/api/financas/${usuarioLogado.id}`);
    const financas = await res.json();
    totalRecebido = 0; totalGasto = 0;
    
    financas.forEach(f => {
        if(f.tipo === 'receita') totalRecebido += f.valor;
        else totalGasto += f.valor;
    });
    updateFinanceUI();
}

function updateFinanceUI() {
    document.getElementById('val-recebido').textContent = `R$ ${totalRecebido.toFixed(2).replace('.', ',')}`;
    document.getElementById('val-gasto').textContent = `R$ ${totalGasto.toFixed(2).replace('.', ',')}`;
    
    const balanco = totalRecebido - totalGasto;
    const valBalancoElement = document.getElementById('val-balanco');
    const statusBalancoElement = document.getElementById('status-balanco');

    valBalancoElement.textContent = `R$ ${Math.abs(balanco).toFixed(2).replace('.', ',')}`;

    if (balanco > 0) { statusBalancoElement.textContent = "Você ganhou"; valBalancoElement.style.color = "green"; } 
    else if (balanco < 0) { statusBalancoElement.textContent = "Você perdeu"; valBalancoElement.style.color = "red"; } 
    else { statusBalancoElement.textContent = "Neutro"; valBalancoElement.style.color = "black"; }
}

async function registrarFinanca(tipo, valorInputId) {
    let input = parseFloat(document.getElementById(valorInputId).value);
    if (!isNaN(input) && input > 0) {
        input = Math.round(input * 100) / 100;
        
        await fetch('/api/financas', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tipo: tipo, valor: input, id_usuario: usuarioLogado.id })
        });
        
        if(tipo === 'receita') totalRecebido += input;
        else totalGasto += input;
        
        updateFinanceUI();
        document.getElementById(valorInputId).value = ''; 
        closeModal();
    } else { alert("Digite um valor válido."); }
}

document.getElementById('btn-add-receita').addEventListener('click', () => openModal('modal-receita'));
document.getElementById('btn-confirm-receita').addEventListener('click', () => registrarFinanca('receita', 'input-receita'));

document.getElementById('btn-add-gasto').addEventListener('click', () => openModal('modal-gasto'));
document.getElementById('btn-confirm-gasto').addEventListener('click', () => registrarFinanca('gasto', 'input-gasto'));

// ==========================================
// 5. LÓGICA DE PLANTAÇÕES
// ==========================================
let plantacoes = [];

async function carregarPlantacoesDoBanco() {
    const res = await fetch(`/api/plantacoes/${usuarioLogado.id}`);
    plantacoes = await res.json();
    renderPlantacoes();
    
    const filtroSelect = document.getElementById('filtro-plantacao');
    if (filtroSelect) {
        filtroSelect.innerHTML = '<option value="">Todas as plantações</option>';
        plantacoes.forEach(p => filtroSelect.innerHTML += `<option value="${p.id}">${p.nome}</option>`);
    }
}

document.getElementById('btn-add-plantacao').addEventListener('click', () => openModal('modal-plantacao'));
document.getElementById('btn-confirm-plantacao').addEventListener('click', async () => {
    const nome = document.getElementById('input-plant-nome').value;
    const area = parseFloat(document.getElementById('input-plant-area').value);
    const plantio = document.getElementById('input-plant-data').value;
    const colheita = document.getElementById('input-plant-colheita').value;

    if (!nome) { alert("Dê um nome para a plantação."); return; }
    if (isNaN(area) || area <= 0) { alert("A área plantada deve ser maior que 0."); return; }
    if (!plantio || !colheita) { alert("Datas obrigatórias."); return; }
    if (new Date(colheita) <= new Date(plantio)) { alert("Colheita deve ser após o plantio."); return; }
    
    const dados = { nome, area, plantio, colheita, id_usuario: usuarioLogado.id };

    const res = await fetch('/api/plantacao', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(dados) });
    const result = await res.json();

    if(result.sucesso) {
        plantacoes.push({ id: result.id, nome, area, data_plantio: plantio, data_colheita: colheita });
        renderPlantacoes();
        
        const filtroSelect = document.getElementById('filtro-plantacao');
        if (filtroSelect) {
            filtroSelect.innerHTML += `<option value="${result.id}">${nome}</option>`;
        }

        document.getElementById('input-plant-nome').value = ''; document.getElementById('input-plant-area').value = '';
        closeModal();
    }
});

function renderPlantacoes() {
    const container = document.getElementById('plantations-container');
    container.innerHTML = '';
    const hoje = new Date(); hoje.setHours(0,0,0,0); 
    
    if(plantacoes.length === 0) {
        document.getElementById('empty-plantation-msg').style.display = 'block';
    } else {
        document.getElementById('empty-plantation-msg').style.display = 'none';
        plantacoes.forEach(p => {
            const dataColheitaObj = new Date(p.data_colheita + "T00:00:00"); 
            let statusTexto = "";
            if (hoje >= dataColheitaObj) statusTexto = "Pronta para colheita";
            else {
                const temInsumo = emUso.some(i => i.id_plantacao === p.id);
                statusTexto = temInsumo ? "Com insumo" : "Sem insumo";
            }

            container.innerHTML += `
            <section class="card plantation-card" id="plant_${p.id}">
                <h2>${p.nome}</h2>
                <div class="plantation-grid">
                    <div><p>Área</p><strong>${p.area} u.m.</strong></div>
                    <div><p>Plantio</p><strong>${formatDate(p.data_plantio)}</strong></div>
                    <div><p>Colheita</p><strong>${formatDate(p.data_colheita)}</strong></div>
                    <div><p>Status</p><strong style="${statusTexto === 'Pronta para colheita' ? 'color: #006400;' : ''}">${statusTexto}</strong></div>
                </div>
                <button class="btn-colheita" onclick="confirmarColheita(${p.id}, '${p.nome}')">Colheita feita</button>
            </section>`;
        });
    }
}

window.confirmarColheita = async function(idPlantacao, nomePlantacao) {
    if(confirm(`A colheita da ${nomePlantacao} já foi feita? Ela será removida.`)) {
        await fetch(`/api/plantacao/${idPlantacao}`, { method: 'DELETE' });
        await carregarPlantacoesDoBanco();
        await carregarInsumosDoBanco();
    }
};

// ==========================================
// 6. LÓGICA DE INSUMOS
// ==========================================
let estoque = [];
let emUso = [];
let currentPage = 1;
const ITEMS_PER_PAGE = 20;

async function carregarInsumosDoBanco() {
    const res = await fetch(`/api/insumos/${usuarioLogado.id}`);
    const data = await res.json();
    estoque = data.estoque;
    emUso = data.em_uso;
    renderTabelasInsumos();
}

const tabEstoque = document.getElementById('tab-estoque'); const tabEmUso = document.getElementById('tab-em-uso');
const viewEstoque = document.getElementById('tabela-estoque-view'); const viewEmUso = document.getElementById('tabela-em-uso-view');

tabEstoque.addEventListener('click', () => { 
    tabEstoque.classList.replace('inactive', 'active'); tabEmUso.classList.replace('active', 'inactive'); 
    viewEstoque.style.display = 'table'; viewEmUso.style.display = 'none'; 
    document.getElementById('filtro-plantacao').style.display = 'none'; 
});
tabEmUso.addEventListener('click', () => { 
    tabEmUso.classList.replace('inactive', 'active'); tabEstoque.classList.replace('active', 'inactive'); 
    viewEmUso.style.display = 'table'; viewEstoque.style.display = 'none'; 
    document.getElementById('filtro-plantacao').style.display = 'inline-block'; 
});

function renderTabelasInsumos() {
    estoque.sort((a, b) => {
        let nomeCompare = a.nome.localeCompare(b.nome);
        if (nomeCompare !== 0) return nomeCompare;
        let dateA = a.validade === '--' ? Infinity : new Date(a.validadeRaw);
        let dateB = b.validade === '--' ? Infinity : new Date(b.validadeRaw);
        return dateA - dateB;
    });

    const bodyEstoque = document.getElementById('tabela-estoque-body');
    const bodyEmUso = document.getElementById('tabela-em-uso-body');
    const searchVal = document.getElementById('search-insumo').value.toLowerCase();
    
    // Filtra Estoque por Nome OU Registro
    let estoqueFiltrado = estoque.filter(item => 
        item.nome.toLowerCase().includes(searchVal) || 
        (item.registro && String(item.registro).toLowerCase().includes(searchVal))
    );
    const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
    const paginatedItems = estoqueFiltrado.slice(startIndex, startIndex + ITEMS_PER_PAGE);
    
    const totalPages = Math.ceil(estoqueFiltrado.length / ITEMS_PER_PAGE) || 1;
    document.getElementById('page-info').textContent = `Pág ${currentPage}/${totalPages}`;

    const hojeStr = new Date().toISOString().split('T')[0]; 

    if (paginatedItems.length === 0) bodyEstoque.innerHTML = `<tr><td colspan="5" class="empty-msg">Nenhum insumo encontrado.</td></tr>`;
    else {
        bodyEstoque.innerHTML = '';
        paginatedItems.forEach(item => { 
            let linhaCor = '';
            if (item.validadeRaw && item.validadeRaw !== '--' && item.validadeRaw < hojeStr) {
                linhaCor = 'background-color: #ffa1ab;'; 
            }

            bodyEstoque.innerHTML += `
            <tr style="${linhaCor}">
                <td>${item.nome}</td>
                <td>${item.quantidade}${item.unidade}</td>
                <td>${item.registro}</td>
                <td>${item.validade}</td>
                <td>
                    <button onclick="deletarInsumoEstoque(${item.id})" style="background: none; border: none; cursor: pointer; color: #d32f2f; font-weight: bold;">Excluir</button>
                </td>
            </tr>`; 
        });
    }

    const filtroSelect = document.getElementById('filtro-plantacao');
    const plantacaoVal = filtroSelect ? filtroSelect.value : '';

    // Filtra Em Uso por Nome OU Registro
    let emUsoFiltrado = emUso.filter(item => 
        item.nome.toLowerCase().includes(searchVal) || 
        (item.registro && String(item.registro).toLowerCase().includes(searchVal))
    );
    if (plantacaoVal !== '') {
        emUsoFiltrado = emUsoFiltrado.filter(item => item.id_plantacao === parseInt(plantacaoVal));
    }

    if (emUsoFiltrado.length === 0) bodyEmUso.innerHTML = `<tr><td colspan="4" class="empty-msg">Nenhum insumo em uso encontrado.</td></tr>`;
    else {
        bodyEmUso.innerHTML = '';
        emUsoFiltrado.forEach(item => { bodyEmUso.innerHTML += `<tr><td>${item.nome}</td><td>${item.quantidade_usada}${item.unidade}</td><td>${item.local_nome}</td><td>${item.data_uso}</td></tr>`; });
    }
}

document.getElementById('search-insumo').addEventListener('input', () => { currentPage = 1; renderTabelasInsumos(); });
const filtroPlantacaoElement = document.getElementById('filtro-plantacao');
if(filtroPlantacaoElement) {
    filtroPlantacaoElement.addEventListener('change', () => { currentPage = 1; renderTabelasInsumos(); });
    filtroPlantacaoElement.style.display = 'none'; 
}

document.getElementById('btn-prev-page').addEventListener('click', () => { if (currentPage > 1) { currentPage--; renderTabelasInsumos(); } });

// Lógica de próxima página atualizada para respeitar a busca por Registro
document.getElementById('btn-next-page').addEventListener('click', () => { 
    const s = document.getElementById('search-insumo').value.toLowerCase(); 
    const mx = Math.ceil(estoque.filter(i => 
        i.nome.toLowerCase().includes(s) || 
        (i.registro && String(i.registro).toLowerCase().includes(s))
    ).length / ITEMS_PER_PAGE); 
    if (currentPage < mx) { currentPage++; renderTabelasInsumos(); } 
});

window.deletarInsumoEstoque = async function(idInsumo) {
    if (confirm("Tem certeza que deseja apagar este insumo do estoque? Esta ação não pode ser desfeita.")) {
        try {
            await fetch(`/api/insumo_estoque/${idInsumo}`, { method: 'DELETE' });
            await carregarInsumosDoBanco();
        } catch(e) {
            alert("Erro ao excluir insumo.");
        }
    }
};

document.getElementById('btn-abrir-estoque').addEventListener('click', () => openModal('modal-insumo-estoque'));
document.getElementById('btn-confirm-estoque').addEventListener('click', async () => {
    const nome = document.getElementById('input-insumo-nome').value;
    let qtd = parseFloat(document.getElementById('input-insumo-qtd').value);
    const unidade = document.getElementById('input-insumo-unidade').value;
    const registro = parseInt(document.getElementById('input-insumo-registro').value);
    const validadeRaw = document.getElementById('input-insumo-validade').value;
    const validadeFormatada = formatDate(validadeRaw);

    if (!nome) { alert("Nome obrigatório."); return; }
    if (isNaN(qtd) || qtd <= 0) { alert("Quantidade inválida."); return; }
    if (isNaN(registro) || registro <= 0) { alert("Registro inválido."); return; }

    qtd = Math.round(qtd * 100) / 100;

    const dados = { nome, qtd, unidade, registro, validade: validadeFormatada, validadeRaw, id_usuario: usuarioLogado.id };
    
    await fetch('/api/insumo_estoque', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(dados) });
    
    await carregarInsumosDoBanco();
    
    document.getElementById('input-insumo-nome').value = ''; document.getElementById('input-insumo-qtd').value = '';
    document.getElementById('input-insumo-registro').value = ''; document.getElementById('input-insumo-validade').value = '';
    closeModal();
});

// ABRIR O MODAL DE USO - Limpa as caixas
document.getElementById('btn-abrir-uso').addEventListener('click', () => {
    document.getElementById('input-uso-busca').value = '';
    document.getElementById('container-lotes-uso').innerHTML = '<p class="empty-msg" style="text-align: center; color: white; margin-top: 10px;">Digite o nome ou registro e clique em buscar.</p>';
    const selectLocal = document.getElementById('input-uso-local');
    selectLocal.innerHTML = '<option value="">Selecione a plantação</option>';
    plantacoes.forEach(p => selectLocal.innerHTML += `<option value="${p.id}">${p.nome}</option>`);
    openModal('modal-insumo-uso');
});

// FUNÇÃO PARA BUSCAR OS LOTES DO INSUMO
document.getElementById('btn-buscar-lotes').addEventListener('click', async () => {
    const termo = document.getElementById('input-uso-busca').value;
    if (!termo) { alert("Digite o nome ou registro para buscar."); return; }
    
    const res = await fetch(`/api/insumo_estoque/busca/${usuarioLogado.id}?q=${encodeURIComponent(termo)}`);
    const lotes = await res.json();
    
    const container = document.getElementById('container-lotes-uso');
    container.innerHTML = '';
    
    if (lotes.length === 0) {
        container.innerHTML = '<p class="empty-msg" style="text-align: center; color: white; margin-top: 10px;">Nenhum insumo encontrado.</p>';
        return;
    }
    
    const hojeStr = new Date().toISOString().split('T')[0];

    // Cria as caixinhas para cada pacote/lote achado
    lotes.forEach(lote => {
        const isVencido = lote.validadeRaw && lote.validadeRaw !== '--' && lote.validadeRaw < hojeStr;
        const bgColor = isVencido ? 'background-color: #ffcccc; color: #cc0000; border: 1px solid #cc0000;' : 'background-color: white; color: #333;';
        const titleVencido = isVencido ? '<strong style="color:red;">(VENCIDO)</strong>' : '';

        container.innerHTML += `
            <div style="padding: 10px; border-radius: 8px; ${bgColor} font-size: 12px; display: flex; flex-direction: column; gap: 5px;">
                <div>
                    <strong>${lote.nome}</strong> ${titleVencido}<br>
                    Registro: ${lote.registro} | Validade: ${lote.validade}<br>
                    Estoque disponível: <strong>${lote.quantidade} ${lote.unidade}</strong>
                </div>
                <div style="display: flex; align-items: center; gap: 5px;">
                    <label style="margin: 0; color: inherit;">Usar:</label>
                    <input type="number" class="input-lote-qtd" data-id="${lote.id}" data-max="${lote.quantidade}" data-vencido="${isVencido}" min="0" step="0.01" style="width: 80px; padding: 5px; border-radius: 5px; border: 1px solid #ccc; background: white; color: black;" placeholder="0">
                    <span>${lote.unidade}</span>
                </div>
            </div>
        `;
    });

    // Adiciona o alerta se o produtor tentar colocar número no lote vencido
    document.querySelectorAll('.input-lote-qtd').forEach(input => {
        input.addEventListener('input', function() {
            limitDecimals(this);
            if (this.value > 0 && this.dataset.vencido === 'true') {
                if (!this.dataset.alerted) {
                    const confirmou = confirm("ATENÇÃO: Este lote está VENCIDO! Tem certeza que deseja utilizá-lo na plantação?");
                    if (!confirmou) {
                        this.value = '';
                    } else {
                        this.dataset.alerted = 'true'; 
                    }
                }
            }
        });
    });
});

// MANDAR PARA O BANCO DE DADOS
document.getElementById('btn-confirm-uso').addEventListener('click', async () => {
    const inputsLotes = document.querySelectorAll('.input-lote-qtd');
    let lotesParaUsar = [];
    let temErroQtd = false;

    // Varre todas as caixinhas de lotes pra ver quais o produtor preencheu
    inputsLotes.forEach(input => {
        let qtd = parseFloat(input.value);
        if (!isNaN(qtd) && qtd > 0) {
            let max = parseFloat(input.dataset.max);
            if (qtd > max) { temErroQtd = true; }
            lotesParaUsar.push({ id: input.dataset.id, qtdUsada: Math.round(qtd * 100) / 100 });
        }
    });

    if (lotesParaUsar.length === 0) { alert("Informe a quantidade de pelo menos um lote na busca para usar."); return; }
    if (temErroQtd) { alert("Você não pode usar mais do que o estoque disponível de um lote."); return; }

    const idPlantacao = parseInt(document.getElementById('input-uso-local').value);
    const localNome = document.getElementById('input-uso-local').options[document.getElementById('input-uso-local').selectedIndex].text;
    const dataUso = formatDate(document.getElementById('input-uso-data').value);

    if (isNaN(idPlantacao)) { alert("Selecione onde foi usado."); return; }

    const dados = { lotes: lotesParaUsar, local_nome: localNome, id_plantacao: idPlantacao, dataUso: dataUso, id_usuario: usuarioLogado.id };
    
    const res = await fetch('/api/insumo_uso', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(dados) });
    const result = await res.json();
    
    if (result.sucesso) {
        await carregarInsumosDoBanco();
        renderPlantacoes(); 
        closeModal();
        tabEmUso.click();
    } else {
        alert(result.mensagem); 
    }
});