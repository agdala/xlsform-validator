/* Teste ponta a ponta da versão web, em um navegador real (Playwright/Chromium).
 *
 * Uso:
 *   python scripts/build_web.py
 *   python -m http.server -d site 8000 &
 *   node tests/web/e2e.js http://localhost:8000/
 */
const { chromium } = require("playwright");
const fs = require("fs");
const os = require("os");
const path = require("path");

const base = process.argv[2] || "http://localhost:8000/";
const root = path.resolve(__dirname, "..", "..");
let failures = 0;

function check(cond, label) {
  console.log(`${cond ? "ok  " : "FALHA"} ${label}`);
  if (!cond) failures += 1;
}

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ acceptDownloads: true, viewport: { width: 1200, height: 900 } });
  // Registra as etapas de carregamento exibidas, na ordem em que aparecem.
  await page.addInitScript(() => {
    window.__etapas = [];
    setInterval(() => {
      const atual = document.querySelector('#etapas li[data-status="atual"]');
      const texto = atual && atual.textContent.trim();
      if (texto && window.__etapas[window.__etapas.length - 1] !== texto) window.__etapas.push(texto);
    }, 20);
  });
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
  const external = [];
  page.on("request", (r) => {
    const url = new URL(r.url());
    if (!["localhost", "127.0.0.1"].includes(url.hostname) && !url.protocol.startsWith("data")) external.push(r.url());
  });

  const t0 = Date.now();
  await page.goto(base);
  // 0. Enquanto carrega: progresso visível e envio bloqueado
  check(await page.isVisible("#etapas"), "etapas de carregamento visíveis");
  const disabledWhileLoading = await page.evaluate(() => ({
    input: document.querySelector("#arquivo").disabled,
    zone: document.querySelector("#zona-envio").getAttribute("aria-disabled"),
    examples: [...document.querySelectorAll("[data-exemplo]")].every((b) => b.disabled),
  }));
  check(
    disabledWhileLoading.input && disabledWhileLoading.zone === "true" && disabledWhileLoading.examples,
    "upload e exemplos desabilitados durante o carregamento",
  );
  await page.waitForSelector('#carga[data-estado="pronto"]', { timeout: 180000 });
  console.log(`motor carregado em ${Date.now() - t0} ms`);
  const etapas = await page.evaluate(() => window.__etapas);
  check(
    etapas.length >= 2 && etapas.every((e, i, a) => i === 0 || e !== a[i - 1]) && /Python/.test(etapas[0]),
    `etapas exibidas em ordem: ${etapas.join(" > ")}`,
  );
  check(/Validador pronto/.test(await page.textContent("#carga-titulo")), "mensagem de validador pronto");
  const enabled = await page.evaluate(() => !document.querySelector("#arquivo").disabled &&
    [...document.querySelectorAll("[data-exemplo]")].every((b) => !b.disabled));
  check(enabled, "upload e exemplos liberados depois de pronto");

  // 1. Exemplo com problemas
  await page.click("text=formulário com problemas");
  await page.waitForSelector(".banner.erro", { timeout: 60000 });
  const title = await page.textContent(".banner h2");
  check(/Reprovado: 26 erros e 11 avisos/.test(title), `exemplo ruim reprovado (${title.trim()})`);
  check((await page.locator(".regra").count()) === 26, "26 regras com problema listadas");

  check((await page.locator('[data-acao="pronto"]').count()) === 0, "reprovado: sem botão de formulário pronto");
  check(/Baixar planilha anotada/.test(await page.textContent(".botao.primario")), "reprovado: botão principal é a planilha anotada");
  const [download] = await Promise.all([page.waitForEvent("download"), page.click("text=Baixar planilha anotada")]);
  const saved = path.join(os.tmpdir(), "e2e_anotado.xlsx");
  await download.saveAs(saved);
  const head = fs.readFileSync(saved).subarray(0, 2).toString();
  check(download.suggestedFilename() === "abrigo_ruim_anotado.xlsx" && head === "PK", "planilha anotada baixada (.xlsx válido)");

  await page.click(".chip >> text=Erros");
  check((await page.locator(".regra.aviso").count()) === 0, "filtro de erros esconde avisos");

  // 2. Upload do formulário aprovado: botão principal é o formulário pronto
  const goodPath = path.join(root, "examples", "abrigo_bom.xlsx");
  await page.setInputFiles("#arquivo", goodPath);
  await page.waitForSelector(".banner.ok", { timeout: 60000 });
  check(true, "upload do formulário bom: aprovado");
  const primary = (await page.textContent(".botao.primario")).trim();
  check(primary === "Baixar formulário pronto para publicar (.xlsx)", `aprovado: botão principal "${primary}"`);
  check((await page.locator("text=Planilha anotada (.xlsx)").count()) === 1, "aprovado: planilha anotada como opção secundária");
  const helpOk = await page.textContent("#ajuda-download");
  check(!/apague/i.test(helpOk) && /sem nenhuma alteração/.test(helpOk), "aprovado: texto não pede para apagar a aba");
  const [readyDl] = await Promise.all([page.waitForEvent("download"), page.click('[data-acao="pronto"]')]);
  const readySaved = path.join(os.tmpdir(), "e2e_pronto.xlsx");
  await readyDl.saveAs(readySaved);
  check(
    readyDl.suggestedFilename() === "abrigo_bom_pronto.xlsx" && fs.readFileSync(readySaved).equals(fs.readFileSync(goodPath)),
    "formulário pronto é idêntico ao original (sem aba, cores ou comentários)",
  );

  // 3. Só avisos: formulário pronto + avisos explicados como recomendações
  await page.setInputFiles("#arquivo", path.join(__dirname, "abrigo_avisos.xlsx"));
  await page.waitForSelector(".banner.aviso", { timeout: 60000 });
  check((await page.locator('[data-acao="pronto"]').count()) === 1, "só avisos: botão de formulário pronto");
  check(/recomendação/.test(await page.textContent("#ajuda-download")), "só avisos: avisos explicados como recomendação");

  // 4. Arquivo inválido
  const bogus = path.join(os.tmpdir(), "e2e_invalido.xlsx");
  fs.writeFileSync(bogus, "não é planilha");
  await page.setInputFiles("#arquivo", bogus);
  await page.waitForSelector(".banner.erro", { timeout: 60000 });
  check(/não parece ser uma planilha/.test(await page.textContent(".banner")), "arquivo inválido explicado ao usuário");

  // 5. Celular: sem rolagem horizontal
  const mobile = await browser.newPage({ viewport: { width: 375, height: 800 } });
  await mobile.goto(base);
  await mobile.waitForSelector('#carga[data-estado="pronto"]', { timeout: 180000 });
  await mobile.click("text=formulário com problemas");
  await mobile.waitForSelector(".banner.erro", { timeout: 60000 });
  const width = await mobile.evaluate(() => document.documentElement.scrollWidth);
  check(width <= 375, `layout cabe no celular (largura ${width}px)`);

  check(errors.length === 0, `sem erros de JavaScript ${errors.length ? JSON.stringify(errors) : ""}`);
  check(external.length === 0, `nenhuma requisição para fora do site ${external.length ? JSON.stringify(external) : ""}`);

  await browser.close();
  console.log(failures ? `\n${failures} verificação(ões) falharam` : "\nTodas as verificações passaram");
  process.exit(failures ? 1 : 0);
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
