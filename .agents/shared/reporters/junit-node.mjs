// Reporter do node:test que grava JUnit XML com o atributo file em cada caso,
// para o rodar_red.py e o rodar_green.py saberem de que arquivo veio cada teste.
// Uso: node --test --test-reporter=./.agents/shared/reporters/junit-node.mjs \
//        --test-reporter-destination=<caminho.xml> <arquivos>
import path from "node:path";

const esc = (s) => String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

export default async function* junit(fonte) {
  const casos = [];
  for await (const ev of fonte) {
    if (ev.type !== "test:pass" && ev.type !== "test:fail") continue;
    const d = ev.data;
    if (d.details?.type === "suite") continue;
    const arquivo = d.file ? path.relative(process.cwd(), d.file).split(path.sep).join("/") : "";
    let filho = "";
    if (ev.type === "test:fail") {
      const err = d.details?.error;
      const causa = err?.cause ?? err;
      const msg = (causa?.message ?? String(causa ?? "falhou")).split("\n")[0];
      // como no pytest: exceção dentro do teste é falha; o arquivo que nem carrega (import, sintaxe) é erro
      const doArquivo = d.nesting === 0 && d.file && [d.file, arquivo, path.relative(process.cwd(), d.file)].includes(d.name);
      const tipo = err?.failureType === "testCodeFailure" && !doArquivo ? "failure" : "error";
      filho = `<${tipo} message="${esc(msg)}"/>`;
    } else if (d.skip || d.todo) {
      filho = "<skipped/>";
    }
    casos.push(`  <testcase classname="${esc(arquivo)}" name="${esc(d.name)}" file="${esc(arquivo)}">${filho}</testcase>`);
  }
  yield `<?xml version="1.0" encoding="utf-8"?>\n<testsuite name="node" tests="${casos.length}">\n${casos.join("\n")}\n</testsuite>\n`;
}
