# Observações iniciais do ambiente

Análise inicial do Juice Shop ( local, acessado pelo container `kali` em `juiceshop:3000`). Reconhecimento feito com `nmap`, `curl` e inspeção do bundle, antes de formular as hipóteses. Juice Shop restaurado ao estado inicial antes de começar (0 desafios resolvidos).

| # | Data e hora | Como observamos | O que vimos | Por que pode ser relevante |
|---|---|---|---|---|
| 1 | 05/11 08:20 | `nmap -sT -sV -p 3000` | Porta 3000 aberta; nmap não reconhece o serviço ("ppp?") | O `-sV` erra o serviço; reconhecer stack exige olhar a resposta HTTP, não só a porta |
| 2 | 05/11 08:20 | `curl -I /` (cabeçalhos) | Presentes: X-Content-Type-Options, X-Frame-Options:SAMEORIGIN, Feature-Policy. Ausentes: Content-Security-Policy, Strict-Transport-Security | Falta de CSP e HSTS; superfície de configuração (A05) |
| 3 | 05/11 08:20 | cabeçalho `X-Recruiting: /#/jobs` e `Access-Control-Allow-Origin: *` | O app vaza uma rota no cabeçalho; CORS liberado para qualquer origem | Pistas de rota em metadados; CORS permissivo |
| 4 | 05/11 08:20 | `/rest/admin/application-version` | Retorna `{"version":"20.3.0"}` sem autenticação | Versão exposta publicamente; útil para mapear componentes (A06) |
| 5 | 05/11 08:20 | `/api/Users` vs `/api/Products` | Users responde 401 (protegido); Products responde 200 com a lista inteira em JSON | Nem toda rota /api tem o mesmo controle de acesso; ponto para testar autorização por objeto |
| 6 | 05/11 08:20 | `/robots.txt` | `Disallow: /ftp` | O próprio app aponta um diretório que "não quer" que seja visto |
| 7 | 05/11 08:20 | `GET /ftp` | Listagem de diretório com arquivos: acquisitions.md, coupons_2013.md.bak, package.json.bak, incident-support.kdbx, encrypt.pyc, announcement_encrypted.md | Diretório servindo arquivos; listagem habilitada; nomes sugerem conteúdo sensível (A05/exposição de dados) |
| 8 | 05/11 08:20 | `GET /rota-que-nao-existe-123` | Responde 200 com 9984 B, igual à página inicial (`/`) | SPA devolve o index para qualquer rota; enumeração de diretórios precisa filtrar por tamanho, senão tudo "existe" |
| 9 | 05/11 08:20 | bundle do index | Carrega `main.js`, `polyfills.js`, `runtime-*.js` (Angular) | Todo o front chega ao cliente; o `main.js` pode revelar rotas e endpoints internos |

> Próximo: a dupla formula as hipóteses a partir destas observações (ver `plano_testes_grupo.md`). Estas linhas são fatos observados, não hipóteses nem caminhos de ataque.
