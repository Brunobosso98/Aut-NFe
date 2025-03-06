# Descrição do Projeto: Automação de Gestão Fiscal para Documentos Eletrônicos
## Visão Geral
Python | PyQt5 | Requests | SQLite | Gestão de Arquivos | API Integration

Desenvolvi uma solução completa para automação de processos fiscais, responsável por:

## Funcionalidades Principais
### 1. Integração com API SIEG:
- Consome API externa (SIEG) para obtenção de XMLs de documentos fiscais (NFSe e CTe).
- Implementa mecanismo robusto de requisições com retry automático e tratamento de erros.
- Gerencia paginação de resultados para processamento de grandes volumes de dados.
### 2. Gestão Inteligente de Arquivos:
- Organiza os XMLs baixados em diretórios estruturados por tipo (NFE/CTE), operação (entrada/saída), ano/mês e CNPJ.
- Extrai metadados dos documentos XML para classificação e armazenamento adequados.
- Permite configuração flexível do diretório base de salvamento, com suporte a servidores de rede.
### 3. Persistência e Controle de Duplicidade:
- Utiliza banco de dados SQLite para rastrear documentos já processados através de hashing.
- Implementa limpeza automática de registros antigos (90 dias) para otimização de performance.
- Evita duplicidade de downloads e processamento, economizando recursos.
### 4. Interface Gráfica Intuitiva:
- Desenvolvida com PyQt5, oferecendo experiência amigável para usuários finais.
- Permite entrada manual de CNPJs ou importação via arquivo Excel.
- Oferece seleção flexível de período de consulta e tipos de documentos (NFSe/CTe).
- Apresenta log detalhado de operações em tempo real com formatação visual.
### 5. Tratamento de Erros Robustos:
- Implementa validação de entradas (CNPJs, datas, diretórios).
- Gerencia falhas de conexão com retry automático e timeout configurável.
- Fornece feedback visual claro sobre o progresso e eventuais problemas.
## Impacto
- Redução significativa no tempo de obtenção e organização de documentos fiscais.
- Eliminação de erros manuais na classificação e armazenamento de XMLs.
- Garantia de compliance na organização fiscal com estrutura padronizada.
- Facilidade de auditoria através de logs detalhados e rastreabilidade de operações.
## Habilidades Demonstradas
- Desenvolvimento de aplicações desktop com interface gráfica em Python
- Integração com APIs externas e tratamento de respostas JSON/XML
- Implementação de banco de dados para persistência e controle de estado
- Manipulação avançada de arquivos e diretórios em ambiente Windows
- Extração e processamento de dados estruturados (XML)
- Tratamento robusto de erros e exceções
## Tecnologias Utilizadas
- Python : Linguagem principal de desenvolvimento
- PyQt5 : Framework para interface gráfica
- Requests : Biblioteca para comunicação HTTP
- SQLite : Banco de dados leve para persistência
- Pandas : Processamento de dados tabulares (Excel)
- ElementTree : Parsing e manipulação de XML
- OS/Shutil : Manipulação de sistema de arquivos
Esta solução representa uma abordagem completa para automação de processos fiscais, combinando interface amigável com processamento robusto de dados, resultando em ganhos significativos de eficiência operacional e conformidade fiscal.