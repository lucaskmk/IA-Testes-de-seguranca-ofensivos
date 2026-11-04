# Fase 3.1 — como pensar o planejamento (sem IA)

> Este guia é só **método**. As hipóteses, estratégias e evidências da Fase 3.1 são escritas pelo grupo, a partir da nossa própria análise do ambiente. O enunciado exige isso, e a comparação "plano do grupo × agente" vale nota em dois critérios (Planejamento 20% e Análise crítica 20%).

---

## 1. Três linhas de raciocínio possíveis

| | A. Lista de falhas conhecidas | B. Observação → hipótese → evidência | C. Exploração livre com o agente |
|---|---|---|---|
| Como funciona | Escolher desafios conhecidos do Juice Shop e mirar neles | Explorar o app manualmente, anotar o que se vê, derivar hipóteses testáveis e definir antes o que as confirma ou refuta | Deixar o agente decidir e documentar depois |
| Atende ao PDF? | Parcialmente — o PDF diz que não avalia quantidade de falhas | **Sim** — é literalmente "análise inicial do ambiente" + "hipóteses" + "evidências necessárias" | **Não** — o plano deve existir antes do agente |
| Risco | Parece roteiro copiado; o LLM também conhece as soluções, então a análise mede memória e não raciocínio | Exige disciplina para registrar observações | Perde o critério de planejamento |
| Valor para a análise crítica | Baixo | **Alto**: dá um padrão para comparar cada proposta do agente | Nenhum ponto de comparação |

**Nossa escolha: B**, com duas camadas extras (seções 3 e 4).

---

## 2. O fluxo da linha B

1. **Observação** — algo que vimos de fato no ambiente (com data e como vimos).
2. **Hipótese** — uma afirmação que pode ser falsa:
   *"Se [condição observável], então [comportamento esperado], porque [conceito visto na disciplina]."*
3. **Critério de evidência (antes de testar)**
   - o que **confirma**;
   - o que **refuta**;
   - o que seria **inconclusivo**.
4. **Ferramentas** — quais das ferramentas do agente poderiam produzir essa evidência, e qual ferramenta nós usaríamos manualmente.
5. **Limites** — o que está fora de escopo nessa investigação.

Definir o critério **antes** de testar é o que torna uma hipótese refutada um resultado válido. Também evita viés de confirmação (aceitar qualquer resposta como prova).

### Perguntas para o grupo responder em cada investigação
- Que observação concreta nos levou a essa hipótese?
- Qual conteúdo da disciplina sustenta o "porquê"?
- Qual resposta da aplicação nos faria dizer "estávamos errados"?
- Que evidência mínima precisamos guardar (status, cabeçalho, trecho de corpo, comparação entre duas respostas)?
- Qual é o caminho mais curto de teste? E qual seria um desvio que **não** aceitaremos do agente?

---

## 3. Camada extra 1 — cada investigação testa uma capacidade diferente do agente

O PDF pede situações distintas "permitindo observar o comportamento do agente diante de diferentes problemas". Então, além de escolher o **aspecto da aplicação**, vale escolher **qual capacidade do agente** cada investigação vai pressionar:

| Situação sugerida no PDF | Capacidade do agente posta à prova | Falha típica de LLM a observar |
|---|---|---|
| Reconhecimento e enumeração | Escolher ferramentas e priorizar o que olhar com muitas informações | Repetição de ações; listar coisas que não apareceram no resultado |
| Autenticação ou autorização | Manter estado entre turnos (contexto, identidades, sequência de passos) | Esquecer o que já obteve; propor passos fora de ordem |
| Tratamento de entradas e requisições | Interpretar respostas e erros da aplicação | Concluir "vulnerável" sem evidência; interpretar mensagem de erro de forma errada |

O grupo decide **qual aspecto concreto** investigar em cada situação. A tabela só ajuda a garantir que as três não testem a mesma coisa do agente.

---

## 4. Camada extra 2 — previsão do grupo sobre a IA

Antes de usar o LLM, registrar para cada investigação:
- onde **esperamos** que o modelo ajude;
- onde **esperamos** que ele erre;
- que tipo de intervenção achamos que vamos precisar fazer.

Na análise crítica, comparamos previsão × realidade. Isso responde diretamente "comparar a estratégia inicial do grupo com as contribuições do agente" e gera achados mesmo quando o modelo se comporta bem.

---

## 5. Prova de que o plano veio antes da IA

1. Escrever o `planejamento/plano_testes_grupo.md`.
2. Commitar e fazer **push** para o remoto **antes** de rodar a revisão 3.2 (e antes de ver qualquer proposta do agente sobre os temas das investigações).
3. Citar o hash e o horário do push no relatório.

---

## 6. Armadilhas

- Hipótese que não pode ser refutada ("a aplicação pode ter falhas de autorização").
- Evidência vaga ("ver se funciona").
- Hipótese tirada de walkthrough, sem observação própria.
- Três investigações sobre o mesmo endpoint ou a mesma capacidade do agente.
- Ferramentas listadas sem dizer **qual evidência** cada uma produz.

---

## 7. Modelo em branco (preencher sem IA)

| Campo | Investigação 1 | Investigação 2 | Investigação 3 |
|---|---|---|---|
| Situação (PDF) | Reconhecimento/enumeração | Autenticação/autorização | Entradas/requisições |
| Observação que motivou | | | |
| Aspecto investigado | | | |
| Hipótese (se… então… porque…) | | | |
| Evidência que confirma | | | |
| Evidência que refuta | | | |
| Resultado inconclusivo seria | | | |
| Ferramentas do agente úteis | | | |
| Ferramenta que usaríamos manualmente | | | |
| Fora de escopo | | | |
| Previsão: onde a IA ajuda | | | |
| Previsão: onde a IA erra | | | |

---

## 8. Roteiro prático (cerca de 2 a 3 horas, a dupla junta)

Regra durante este roteiro: **nenhuma IA aberta** (nem o agente, nem chat). Tudo o que for escrito sai da observação de vocês.

1. **Acesso:** conectar a VPN e, no PowerShell do notebook:
   `ssh -L 3000:172.31.80.10:3000 lr@10.0.80.3`
   Deixar essa janela aberta e abrir `http://localhost:3000` no navegador.
2. **Ponto de partida limpo:** em outra janela SSH, `cd ~/af && bash lab/restore.sh`.
3. **Exploração (1 a 1,5 h):** navegar pela aplicação com o DevTools aberto (abas Network, Sources e Application). Em outra janela SSH, `docker exec -it kali bash` para usar `curl`, `nmap` e `ffuf` contra `juiceshop:3000`, como nas aulas.
   A cada coisa que chamar atenção, uma linha em `planejamento/observacoes_iniciais.md`: data e hora, quem, como viu, o que viu e por que pode importar. Meta: 10 a 20 observações.
4. **Plano (1 h):** escolher 3 observações, uma por situação do PDF, e preencher a matriz de `planejamento/plano_testes_grupo.md` seguindo as perguntas da seção 2 deste guia e evitando as armadilhas da seção 6. Em "Objetivo que será entregue ao agente", escrever **só o objetivo**, sem a hipótese nem o caminho. Preencher também a previsão sobre a IA.
5. **Antes de mostrar a qualquer IA:**
   ```
   git add planejamento/ && git commit -m "Plano de testes do grupo (Fase 3.1)" && git push
   ```
   Anotar o hash do commit e o horário do push.
6. **Só depois do push:** avisar. A partir daí roda a revisão 3.2 (`agent/revisar_plano.py`); a tabela de decisões é preenchida pela dupla.

## 9. Como serão as investigações

- Uma sessão por investigação, no `tmux` do servidor, com o objetivo escrito no plano.
- A cada proposta do modelo, quem decide é a dupla: **[a]**, **[m]**, **[r]** ou **[f]**, com a justificativa nas palavras de vocês. Depois de cada resultado, também é de vocês a "decisão após o resultado" (o que a evidência mostra e se a interpretação do modelo está certa).
- Pode ser feito direto no terminal, ou pelo chat: a proposta é mostrada a vocês, vocês respondem com a decisão e a justificativa, e essa resposta é digitada **literalmente** no agente.
- Marcar tags na hora (`boa_sugestao`, `alucinacao`, `interpretacao_errada`, `repeticao`, `fora_escopo`, `falha_ia`): são a matéria-prima da análise crítica.
