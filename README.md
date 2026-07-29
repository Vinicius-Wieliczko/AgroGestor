# 🌱 AgroGestor: Plataforma Digital para Organização e Análise de Dados de Pequenas Propriedades Rurais

**AgroGestor** é uma plataforma digital voltada à gestão de dados agrícolas em pequenas propriedades rurais. Desenvolvido como um subprojeto de pesquisa na **Universidade Estadual de Ponta Grossa (UEPG)**, o sistema busca promover a inclusão tecnológica, a sustentabilidade e a autonomia dos agricultores na administração de suas atividades.

## 🎯 Caracterização e Justificativa

Pequenos e médios produtores rurais enfrentam desafios estruturais relacionados à gestão de informações sobre suas atividades produtivas, comerciais e administrativas. Ferramentas digitais de gestão agrícola existentes no mercado são frequentemente voltadas a grandes propriedades, exigem conectividade constante, interfaces complexas e custos de licenciamento elevados. 

O AgroGestor preenche essa lacuna oferecendo uma plataforma simples e acessível para a agricultura familiar, que representa mais de 70% dos estabelecimentos rurais no Brasil. O projeto atende a importantes eixos estruturantes, como Transformação Digital, Desenvolvimento Social e Regional, e Sustentabilidade Socioambiental. 

Além disso, a ferramenta está alinhada a diversos Objetivos de Desenvolvimento Sustentável (ODS) da ONU, incluindo: Erradicação da pobreza (ODS 1), Fome zero e agricultura sustentável (ODS 2), Trabalho decente e crescimento econômico (ODS 8), e Indústria, inovação e infraestrutura (ODS 9).

## 🚀 Funcionalidades Principais (Objetivos Específicos)

* **Registro e Organização de Dados:** Levantamento e estruturação de informações essenciais sobre produção, insumos, clima, custos e vendas para apoiar a tomada de decisões.
* **Controle de Insumos e Lotes:** Inserção e retirada de insumos agrícolas no estoque, com controle automatizado de validades para evitar perdas.
* **Gestão de Plantações:** Registro de áreas plantadas, controle de datas de plantio e previsão de colheita.
* **Módulo Financeiro:** Balanço dinâmico de receitas e despesas.

## 🛠️ Metodologia e Tecnologias

A aplicação foi projetada com base nas demandas reais de produtores e técnicos, focando em simplicidade e baixo custo. O desenvolvimento ocorre por meio de ciclos iterativos, utilizando ferramentas livres:

**Front-end (Interface):**
* HTML, CSS e JavaScript para a criação de uma interface digital (web) simples para entrada, consulta e visualização dos dados.

**Back-end e Banco de Dados:**
* **Python** utilizando o framework **Flask**.
* Banco de dados relacional **SQLite** para armazenamento seguro das informações de forma portátil e de fácil manutenção.
* Criptografia nativa para senhas e CPFs.

## 👨‍💻 Pesquisa e Desenvolvimento

* **Bolsista / Desenvolvedor:** Vinicius Eduardo Wieliczko
* **Orientadora:** Profª Drª Maria Salete Marcon Gomes Vaz
* **Coorientador:** Jorge Davi Navarro
* **Área de Conhecimento (CNPq):** Ciências Exatas e da Terra / Ciência da Computação

## ⚙️ Como executar o projeto localmente

1. Clone o repositório:
   ```bash
   git clone [https://github.com/Vinicius-Wieliczko/AgroGestor.git](https://github.com/Vinicius-Wieliczko/AgroGestor.git)

2. Instale as dependências:
  ```bash
  pip install -r requirements.txt
   
3. Inicie o servidor de desenvolvimento:
   ```bash
   python app.py
   
Acesse a aplicação no navegador através do endereço: http://127.0.0.1:5000
