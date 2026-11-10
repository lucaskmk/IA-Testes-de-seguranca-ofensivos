# A estrutura do web service molda a análise

> **Escopo e ética:** todo o teste ativo deste trabalho ficou restrito à instância **local** do Juice Shop. Os exemplos de CMS abaixo são observações **passivas** (o que qualquer visitante vê numa página pública) e discussão **conceitual** de método — não testamos, nem pretendemos testar, nenhum serviço de terceiros.

Uma das lições do trabalho é que **não existe um método único para "analisar um web service"**: a abordagem, as ferramentas e as classes de problema mudam conforme a arquitetura. Comparando duas estruturas comuns:

| | SPA + API REST (nosso alvo: OWASP Juice Shop) | CMS server-rendered (ex.: WordPress) |
|---|---|---|
| Como a superfície se revela | O cliente baixa um bundle JS (`main.js`) que **declara as rotas e endpoints**; a API `/api` e `/rest` é o núcleo | O servidor renderiza HTML por página; a superfície está em **rotas conhecidas**, no tema e nos **plugins** |
| Reconhecimento | Ler o bundle, enumerar a API, inspecionar o JWT | Versão pelo `readme.html`/meta generator; `/wp-json/`; enumeração de plugins/temas e de usuários (`?author=N`) |
| Autenticação | Token JWT (no nosso caso, RS256) | Cookies de sessão PHP; `wp-login.php`, `xmlrpc.php` |
| Classes típicas | IDOR na API, injeção na busca, exposição de dados na serialização | **CVEs conhecidos** em plugins/temas desatualizados, configuração do servidor, exposição de `wp-content` |
| Ferramentas que fariam sentido | `http_request`/curl, `nmap`, `ffuf`, `decode_jwt` (as do nosso agente) | Um scanner específico (ex.: WPScan), SCA de plugins, mapeamento de CVE |

O site público do próprio professor (`rodolfoavelino.com.br`), observado como visitante, é um exemplo de CMS WordPress (tema Zerif Lite) — ou seja, uma estrutura bem diferente da que investigamos.

## Por que isso importa para o nosso agente

As quatro ferramentas do nosso agente (`http_request`, `nmap_scan`, `dir_enum`, `decode_jwt`) e o plano das três investigações foram **moldados pela estrutura SPA + REST + JWT** do Juice Shop. Diante de um CMS, o mesmo agente seria limitado: faltaria uma ferramenta de enumeração de plugins/CVEs, e o plano precisaria mirar a superfície do WordPress, não um bundle JavaScript. 

Isso é, ao mesmo tempo, uma **limitação** (o agente é específico do alvo) e uma **direção de extensão**: a mesma arquitetura — agente supervisionado com trava de escopo e log por turno — se adaptaria a outra estrutura trocando o conjunto de ferramentas e o plano, sem mudar o núcleo. Como a trava de escopo e o modelo vêm da configuração, essa troca é barata; o custo está em desenhar o novo plano e as novas ferramentas, de novo com supervisão humana.
