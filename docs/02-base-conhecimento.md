# Base de conhecimento

## Dados utilizados

A pasta `data/` parte dos arquivos do laboratório e muda o caso para o alerta no cartão da Marina. Tudo é fictício.

| Arquivo | Formato | Utilização no agente |
|---------|---------|----------------------|
| `perfil_cliente.json` | JSON | Nome, renda, perfil conservador, cartão final 4412 e reserva |
| `transacoes.csv` | CSV | Gastos de outubro de 2025 e a compra com status `alerta` |
| `historico_atendimento.csv` | CSV | Bloqueio antigo, pedido de aviso de compra e o alerta ainda em aberto |
| `produtos_financeiros.json` | JSON | Bloqueio, cartão virtual, contestação, aviso de compra e o catálogo de investimento |
| `regras_banco.json` | JSON | Prazos, canal 0800 000 1234 e o que a Vera não pode pedir |
| `faq_seguranca.json` | JSON | Texto curto para golpe em andamento, estorno e a diferença entre o notebook e o alerta |

O CSV de transações do laboratório tinha data, descrição, categoria, valor e tipo. Aqui entram também `status`, `hora` e `final_cartao`, porque o caso precisa separar compra confirmada de compra em alerta.

## Adaptações nos dados

O laboratório traz João Silva, perfil moderado e um extrato sem fraude. Este protótipo troca o titular para Marina Alves e coloca uma compra em alerta:

- Eletrônicos Online INT, R$ 2.480,00, em 18/10/2025 às 02:14, cartão final 4412.
- A maior saída confirmada do mês é o aluguel, R$ 1.500,00.
- A maior compra confirmada é a Loja Aurora Shopping, R$ 210,00.
- A renda mensal é R$ 6.200,00, então essa compra equivale a 40% da renda.
- A reserva atual é R$ 8.000,00 e a meta é R$ 18.600,00. Faltam R$ 10.600,00.

Os produtos de cartão são do Banco Aurora, instituição fictícia. Tesouro Selic, CDB, LCI/LCA, Fundo Multimercado e Fundo de Ações permanecem no catálogo, com o risco de cada um, para a resposta respeitar o perfil conservador.

O dataset público do notebook continua de fora desta pasta. Ele tem centenas de milhares de linhas e não identifica um cliente para conversar.

## Estratégia de integração

### Como os dados são carregados?

`src/conhecimento.py` lê os arquivos no início da sessão, converte valor para número e monta uma ficha. A ficha já traz os totais, o alerta, o peso na renda e o que falta da reserva. A interface e a avaliação usam a mesma função.

### Como os dados são usados no prompt?

No modo base, o código escolhe o trecho e copia o número da ficha. No modo generativo, a ficha e os arquivos entram no system prompt. O modelo é instruído a copiar os valores, sem refazer a conta. Se a resposta do modelo citar um real que não está na ficha, ela é descartada.

## Exemplo de contexto montado

```
Cliente: Marina Alves, 34 anos, Designer.
Renda mensal: R$ 6.200,00.
Perfil de investidor: conservador.
Cartão final 4412, status ativo_com_alerta.
Reserva atual: R$ 8.000,00.
Meta da reserva: R$ 18.600,00.
Falta para a reserva: R$ 10.600,00.
Saídas em outubro de 2025: R$ 5.319,30.
Saídas sem a compra em alerta: R$ 2.839,30.
Alerta: Eletrônicos Online INT, R$ 2.480,00, em 18/10/2025 às 02:14, no cartão final 4412.
A compra em alerta equivale a 40% da renda mensal.
Prazo para contestar: 7 dias corridos, até 25/10/2025.
Análise: até 10 dias úteis. Estorno garantido: não.
```
