# DuckDB Analytics: Guia de Desenvolvimento do NYC Yellow Taxi Hub

Este guia detalha a estrutura de pastas, os objetivos analíticos, as regras de saneamento de dados e o plano de implementação do pipeline de Data Quality e Analytics utilizando o DuckDB.

---

## 1. Estrutura do Repositório

A árvore de diretórios oficial do repositório deve seguir a estrutura abaixo:

```text
duckdb-analytics/
├── .github/
│   └── workflows/
│       └── data_pipeline_ci.yml
├── data/
│   ├── raw/                 # Camada Bronze (Ignorada no Git)
│   ├── staging/             # Camada Prata  (Ignorada no Git)
│   └── processed/           # Camada Ouro   (Ignorada no Git)
├── docs/
│   └── data_dictionary.md   # Dicionário de dados formal do projeto
├── notebooks/
│   └── 01_exploratory_analysis.ipynb
├── scripts/
│   ├── __init__.py
│   ├── clean.py             # Saneamento atômico de dados (Prata)
│   ├── transform.py         # Regras de negócio e KPI analytics (Ouro)
│   └── main.py              # Orquestrador central do pipeline
├── tests/
│   ├── __init__.py
│   └── test_quality_gates.py
├── .gitignore
├── Dockerfile
├── Makefile                 # Atalhos de execução (make run, make test)
├── pyproject.toml
└── README.md
```

---

## 2. Contexto de Negócio e Dor do Mercado

Uma grande operadora de frotas e consultoria de mobilidade em Nova York está enfrentando sérias inconsistências financeiras e operacionais em seus relatórios mensais. O dado bruto coletado diretamente dos taxímetros (fornecido pela TLC de NYC) chega contaminado por anomalias de hardware: falhas de GPS geram telemetrias absurdas que registram milhares de milhas em corridas curtas locais, interrupções de conexão de rede corrompem os registros dos métodos de pagamento e corridas canceladas inserem distâncias e faturamentos zerados ou negativos no histórico. Tomar decisões estratégicas de alocação de motoristas ou precificação com esses dados brutos está gerando prejuízos severos e perda de credibilidade com investidores.

**Propósito & Objetivo do Produto:**
O propósito deste produto é atuar como uma plataforma de *Data Reliability Engineering*. O objetivo é construir uma pipeline de dados industrializada que remova as distorções físicas através de regras de higienização automatizadas, centralizando o dado limpo em uma camada intermediária de Staging (Prata) para alimentar de forma confiável e ágil os Data Marts analíticos de tomada de decisão (Camada Ouro).

---

## 3. Direcionamento de Modelagem e Engenharia

* **Clean Architecture:** Separação rígida entre a camada de armazenamento físico dos arquivos Parquet (Infraestrutura) e as regras analíticas estruturadas em SQL (Núcleo de Negócio).
* **SOLID (SRP):** Desacoplamento absoluto em arquivos independentes: o módulo `clean.py` cuida puramente do saneamento de integridade dos dados (Prata), o módulo `transform.py` foca apenas na consolidação matemática dos Data Marts de KPIs (Ouro), e o `main.py` atua como o controlador/orquestrador único.
* **SOLID (DIP):** Inversão de dependência na gestão do banco de dados: a conexão em memória do DuckDB é instanciada centralizadamente no orquestrador e injetada via parâmetro nas funções dos módulos de limpeza e transformação.

---

## 4. Escopo de Requisitos da Solução

### Requisitos Cruciais (Importantes / MVP Obrigatório)
* **Ingestão via DuckDB:** Processamento vetorizado nativo consumindo arquivos Parquet diretamente do disco.
* **Módulo de Higienização:** Funções isoladas para tratamento de nulos corporativos (`COALESCE` para valores sentinela), padronização de tipos físicos de colunas (`TIMESTAMP`, `INTEGER`, `DOUBLE`) e aplicação de filtros rígidos de domínio de negócio para rejeitar registros nulos, zerados ou negativos (`total_amount > 0` e `trip_distance > 0`).
* **Filtro de Outliers Temporais e Espaciais:** Exclusão de registros com distâncias acima de 150 milhas e durações fora do intervalo de 1 a 180 minutos calculadas via função de diferença de tempo (`date_diff`).
* **Materialização de Data Marts Básicos:** Construção de agregações para responder a quatro contextos de negócios específicos (Métricas Diárias, Velocidade/Trânsito por hora, Lucratividade de Aeroportos e Comportamento por Meio de Pagamento).

### Requisitos Desejáveis (Diferenciais do Portfólio)
* **Laboratório de Diagnóstico:** Notebook Jupyter com storytelling narrativo e documentação comparativa usando o comando `SUMMARIZE` antes do pipeline produtivo.
* **Visualização Interativa:** Geração de gráficos de linhas e barras dinâmicos usando Plotly Express mapeando o volume de corridas e o comportamento do tráfego urbano.
* **Testes de Qualidade Automatizados:** Escrita de checagens com `pytest` para barrar a exportação de arquivos caso os Data Marts finais gerem valores nulos em colunas chaves.
* **Marts Estratégicos Avançados (Camada Ouro Expandida):**
  1. *Impacto da Taxa CBD:* Análise de faturamento e volume de corridas na Zona de Congestionamento de Manhattan.
  2. *Qualidade de Conexão do Provedor:* Mapeamento de falhas de conexão (`store_and_fwd_flag`) e market share por `VendorID`.
  3. *Elasticidade de Ocupação:* Análise de distância e gorjetas agrupadas pelo tamanho do grupo (`passenger_count`).
  4. *Auditoria de Repartição de Receitas:* Divisão percentual de cada dólar faturado entre o Motorista (Tarifa Líquida + Gorjeta) e Taxas Governamentais / Pedágios.
  5. *Matriz de Hotspots Geográficos:* Rotas mais populares e lucrativas agrupadas por pares `PULocationID` -> `DOLocationID`.

---

## 5. Matriz de KPIs e Métricas de Sucesso

As transformações devem seguir estritamente as fórmulas matemáticas especificadas pela área de negócio:

### Métricas Gerais e Operacionais:
1. **Ticket Médio Diário ($)**:
   $$\text{avg\_ticket} = \frac{\sum(\text{total\_amount})}{\text{COUNT}(\text{viagens})}$$
2. **Velocidade Média de Fluxo Urbano (MPH)**:
   $$\text{avg\_speed\_mph} = \text{AVG}\left(\frac{\text{trip\_distance}}{\frac{\text{date\_diff('minute', pickup, dropoff)}}{60.0}}\right)$$
3. **Taxa de Penetração de Gorjetas Eletrônicas (%)**:
   $$\text{avg\_tip\_percentage} = \text{AVG}\left(\frac{\text{tip\_amount}}{\text{NULLIF}(\text{fare\_amount}, 0)}\right) \times 100$$
4. **Receita por Milha Útil ($/Mile)**:
   $$\text{revenue\_per\_mile} = \text{AVG}\left(\frac{\text{total\_amount}}{\text{NULLIF}(\text{trip\_distance}, 0)}\right)$$

### Métricas Estratégicas Expandidas:
5. **Percentual de Impacto da Taxa de Congestionamento (CBD)**:
   $$\text{cbd\_impact\_\% } = \text{AVG}\left(\frac{\text{cbd\_congestion\_fee}}{\text{NULLIF}(\text{total\_amount}, 0)}\right) \times 100$$
6. **Taxa de Desconexão / Viagens Offline (%)**:
   $$\text{offline\_rate} = \frac{\text{COUNT}(\text{CASE WHEN } store\_and\_fwd\_flag = 'Y' \text{ THEN 1 END})}{\text{COUNT}(*)} \times 100$$
7. **Fatia Líquida do Motorista (% de Composição)**:
   $$\text{driver\_share\_\% } = \text{AVG}\left(\frac{\text{fare\_amount} + \text{tip\_amount}}{\text{total\_amount}}\right) \times 100$$
8. **Taxa de Sobrecarga Governamental (% de Composição)**:
   $$\text{government\_tax\_share\_\% } = \text{AVG}\left(\frac{\text{mta\_tax} + \text{improvement\_surcharge} + \text{congestion\_surcharge} + \text{cbd\_congestion\_fee}}{\text{total\_amount}}\right) \times 100$$

---

## 5.1 Relação: Métrica, Hipótese, Dor de Negócio e Query (Camada Ouro Expandida)

### 1. Impacto Financeiro da Zona de Congestionamento (CBD)
* **Dor de Negócio:** A diretoria de planejamento precisa entender o impacto financeiro da nova taxa de congestionamento do distrito central de negócios (`cbd_congestion_fee`) no preço final pago pelo usuário.
* **Hipótese:** A taxa CBD representa uma parcela significativa (> 10%) do custo total pago pelo usuário em Manhattan, podendo atuar como um desincentivo à demanda de viagens curtas na região.
* **Query SQL para o `transform.py`**:
```sql
SELECT 
    tpep_pickup_datetime::DATE AS date,
    COUNT(*) AS total_trips,
    SUM(CASE WHEN cbd_congestion_fee > 0 THEN 1 ELSE 0 END) AS trips_with_cbd,
    ROUND(AVG(cbd_congestion_fee), 2) AS avg_cbd_fee_paid,
    ROUND(AVG(cbd_congestion_fee / NULLIF(total_amount, 0)) * 100, 2) AS cbd_share_of_total_revenue
FROM '{staging_path}'
GROUP BY 1 ORDER BY 1;
```

### 2. Diagnóstico de Conectividade Operacional dos Provedores (`VendorID`)
* **Dor de Negócio:** A área de Infraestrutura precisa auditar qual provedor de tecnologia da frota (CMT vs. Curb) apresenta maior taxa de falhas de conexão, gerando atraso no envio offline dos dados (`store_and_fwd_flag = 'Y'`).
* **Hipótese:** Um dos provedores possui equipamento de telemetria desatualizado, apresentando taxa de desconexão de dados 2x maior nos cânions urbanos de Manhattan.
* **Query SQL para o `transform.py`**:
```sql
SELECT 
    CASE VendorID
        WHEN 1 THEN 'Creative Mobile Technologies'
        WHEN 2 THEN 'Curb Mobility'
        ELSE 'Other'
    END AS technology_provider,
    COUNT(*) AS total_trips,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS market_share_percentage,
    ROUND(AVG(total_amount), 2) AS avg_ticket,
    ROUND(SUM(CASE WHEN store_and_fwd_flag = 'Y' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 4) AS network_failure_rate_percentage
FROM '{staging_path}'
GROUP BY 1 ORDER BY total_trips DESC;
```

### 3. Matriz de Elasticidade de Ocupação (`passenger_count`)
* **Dor de Negócio:** Validar a aderência a campanhas promocionais de tarifas para grupos. O Marketing quer saber se grupos de passageiros geram gorjetas percentuais melhores do que viajantes sozinhos.
* **Hipótese:** Passageiros viajando em grupos maiores tendem a ser mais generosos na taxa de gorjeta por conta do rateio da corrida.
* **Query SQL para o `transform.py`**:
```sql
SELECT 
    passenger_count AS group_size,
    COUNT(*) AS total_trips,
    ROUND(AVG(trip_distance), 2) AS avg_distance_miles,
    ROUND(AVG(fare_amount), 2) AS avg_base_fare,
    ROUND(AVG(tip_amount / NULLIF(fare_amount, 0)) * 100, 2) AS avg_tip_percentage
FROM '{staging_path}'
GROUP BY 1 ORDER BY group_size ASC;
```

### 4. Auditoria de Composição de Receita (Fatia do Motorista vs. Impostos)
* **Dor de Negócio:** O sindicato dos taxistas alega que a renda real líquida que sobra para quem dirige está sendo corroída pelo excesso de sobretaxas municipais de NYC.
* **Hipótese:** Taxas governamentais e impostos representam mais de 15% do custo total da corrida, reduzindo a parcela retida pelo motorista.
* **Query SQL para o `transform.py`**:
```sql
SELECT 
    ROUND(AVG(fare_amount / NULLIF(total_amount, 0)) * 100, 2) AS driver_base_fare_share,
    ROUND(AVG(tip_amount / NULLIF(total_amount, 0)) * 100, 2) AS driver_tip_share,
    ROUND(AVG((mta_tax + improvement_surcharge + congestion_surcharge + COALESCE(cbd_congestion_fee, 0)) / NULLIF(total_amount, 0)) * 100, 2) AS government_taxes_share,
    ROUND(AVG(tolls_amount / NULLIF(total_amount, 0)) * 100, 2) AS highway_tolls_share
FROM '{staging_path}';
```

### 5. Análise de Conectividade e Confiabilidade (Estabilidade de Sinal)
* **Pergunta de Negócio:** Qual provedor (VendorID) sofre mais com problemas de perda de sinal de rede nos cânions urbanos de Manhattan?
* **Métrica / Colunas:** Cruzar VendorID com a flag store_and_fwd_flag (indica se a corrida foi gravada na memória do carro antes de enviar ao servidor devido à falta de sinal).
* **Fórmula / KPI:** $$\text{Offline Trip Rate} = \frac{\text{COUNT}(\text{viagens onde } store\_and\_fwd\_flag = 'Y')}{\text{COUNT}(\text{total\_viagens})} \times 100$$
* **Impacto:** Ajuda a empresa a avaliar qual fornecedor de tecnologia de telemetria possui melhor estabilidade de infraestrutura de rede móvel em NYC.
* **Query SQL para o `transform.py`**:
```sql
SELECT 
    VendorID,
    COUNT(*) AS total_trips,
    SUM(CASE WHEN store_and_fwd_flag = 'Y' THEN 1 ELSE 0 END) AS offline_trips,
    ROUND(SUM(CASE WHEN store_and_fwd_flag = 'Y' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 4) AS offline_trip_rate
FROM '{staging_path}'
GROUP BY VendorID;
```

### 6. Matriz de Hotspots Geográficos (Rotas Populares e Lucrativas)
* **Pergunta de Negócio:** Quais são os fluxos urbanos (PULocationID para DOLocationID) mais demandados e quais geram maior lucratividade por hora para a frota?
* **Métrica / Colunas:** Agrupamento por PULocationID (embarque) e DOLocationID (desembarque).
* **Fórmula / KPI:** Volume total de viagens por par, Receita total acumulada e Ticket Médio por Rota.
* **Impacto:** Permite otimizar o posicionamento geográfico dos veículos da frota nos horários de pico.
* **Query SQL para o `transform.py`**:
```sql
SELECT 
    PULocationID,
    DOLocationID,
    COUNT(*) AS total_trips,
    ROUND(SUM(total_amount), 2) AS total_revenue,
    ROUND(AVG(total_amount), 2) AS avg_ticket,
    ROUND(AVG(total_amount / NULLIF(trip_distance, 0)), 2) AS revenue_per_mile
FROM '{staging_path}'
GROUP BY PULocationID, DOLocationID
ORDER BY total_trips DESC
LIMIT 20;
```

### 7. Impacto das Taxas de Congestionamento (Surcharges) no Bolso do Passageiro
* **Pergunta de Negócio:** Qual a fatia do preço final da viagem que corresponde a taxas extras e impostos locais de NYC versus o custo real do serviço prestado?
* **Métrica / Colunas:** Comparar tarifas adicionais (congestion_surcharge, mta_tax, improvement_surcharge, Airport_fee) contra o fare_amount (tarifa líquida) e o total_amount.
* **Fórmula / KPI:** $$\text{Tax Burden \%} = \frac{\text{congestion\_surcharge} + \text{mta\_tax} + \text{improvement\_surcharge} + \text{Airport\_fee}}{\text{total\_amount}} \times 100$$
* **Impacto:** Mede o peso das políticas públicas de mobilidade urbana (como a taxa de congestionamento do CBD) no comportamento de custos do usuário.
* **Query SQL para o `transform.py`**:
```sql
SELECT 
    ROUND(AVG((congestion_surcharge + mta_tax + improvement_surcharge + Airport_fee) / NULLIF(total_amount, 0)) * 100, 2) AS avg_tax_burden_percentage
FROM '{staging_path}';
```

### 8. Eficiência de Capacidade (Ocupação e Rentabilidade)
* **Pergunta de Negócio:** Viagens com maior número de passageiros (passenger_count) tendem a ser mais longas (viagens compartilhadas/turísticas) ou geram melhores gorjetas?
* **Métrica / Colunas:** Agrupamento por passenger_count.
* **Fórmula / KPI:** Ticket médio, distância média e taxa de gorjeta por contagem de passageiros.
* **Impacto:** Auxilia em estratégias de precificação diferenciada para grupos ou recomendação de serviços de carona compartilhada.
* **Query SQL para o `transform.py`**:
```sql
SELECT 
    passenger_count,
    ROUND(AVG(total_amount), 2) AS avg_ticket,
    ROUND(AVG(trip_distance), 2) AS avg_distance,
    ROUND(AVG(tip_amount / NULLIF(fare_amount, 0)) * 100, 2) AS avg_tip_percentage
FROM '{staging_path}'
GROUP BY passenger_count
ORDER BY passenger_count;
```

---

## 6. Planejamento de Branches (Git) e Etapas

* **Estrutura de Branches Recomendada:** `main` (protegida), `feature/setup-infra` (para configurações iniciais via PR), `feature/data-cleansing-layer`, `feature/analytical-marts`, `feature/ci-cd-automation`.
* **Etapas Sequenciais (Dependências Estritas):**
  1. *Setup da Infraestrutura:* Configurações de dependências (`pyproject.toml`), `.gitignore` e diretórios iniciais devem ser commitados na branch `feature/setup-infra` e integrados na `main` estritamente por meio de Pull Requests.
  2. *Data Quality Gate (Prata):* O arquivo `clean.py` precisa processar a Bronze e consolidar a tabela limpa no Staging. Nenhuma query de negócio pode ler o dado bruto diretamente.
  3. *Business Aggregations (Ouro):* O arquivo `transform.py` realiza a leitura única e restrita do arquivo higienizado resultante da camada Prata.
* **Etapas Paralelas (Trabalho Simultâneo):**
  * A estruturação do ambiente Docker, a codificação do workflow de CI/CD do GitHub Actions e o design descritivo do dicionário de dados técnico podem evoluir de forma simultânea e independente enquanto os módulos Python principais estão sendo criados nas ramificações de desenvolvimento.

---

## 7. Roteiro de Implementação

1. **Fase 1 (Setup):** Inicializar o projeto estruturando o gerenciador de dependências com `uv` e configurando as pastas locais de dados.
2. **Fase 2 (Exploração):** Criar o laboratório `notebooks/01_exploratory_analysis.ipynb`, ler o arquivo Parquet bruto de Abril de 2026 e disparar o `SUMMARIZE` para expor e documentar estatisticamente as anomalias de máximos e mínimos do dataset.
3. **Fase 3 (Clean):** Construir o arquivo modular `clean.py` dividindo o processo de higienização em funções atômicas (`handle_nulls`, `standardize_types`, `validate_domains`, `remove_outliers`) amarradas por expressões de CTEs lógicas.
4. **Fase 4 (Transform):** Criar o arquivo `transform.py` contendo as queries dedicadas a calcular os Data Marts de KPIs exigidos pela liderança operacional, consumindo apenas o arquivo estável do Staging.
5. **Fase 5 (Orquestração & DevOps):** Unificar a esteira de execução no `main.py` controlando o bloco de transação e escrever os testes com `pytest` na pasta `tests/` para verificar a conformidade final de nulos.
