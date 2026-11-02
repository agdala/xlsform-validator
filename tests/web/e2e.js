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
  await page.waitForSelector('#status-motor[data-estado="pronto"]', { timeout: 180000 });
  console.log(`motor carregado em ${Date.now() - t0} ms`);

  // 1. Exemplo com problemas
  await page.click("text=formulário com problemas");
  await page.waitForSelector(".banner.erro", { timeout: 60000 });
  const title = await page.textContent(".banner h2");
  check(/Reprovado: 26 erros e 11 avisos/.test(title), `exemplo ruim reprovado (${title.trim()})`);
  check((await page.locator(".regra").count()) === 26, "26 regras com problema listadas");

  const [download] = await Promise.all([page.waitForEvent("download"), page.click("text=Baixar planilha anotada")]);
  const saved = path.join(os.tmpdir(), "e2e_anotado.xlsx");
  await download.saveAs(saved);
  const head = fs.readFileSync(saved).subarray(0, 2).toString();
  check(download.suggestedFilename() === "abrigo_ruim_anotado.xlsx" && head === "PK", "planilha anotada baixada (.xlsx válido)");

  await page.click(".chip >> text=Erros");
  check((await page.locator(".regra.aviso").count()) === 0, "filtro de erros esconde avisos");

  // 2. Upload de arquivo do usuário
  await page.setInputFiles("#arquivo", path.join(root, "examples", "abrigo_bom.xlsx"));
  await page.waitForSelector(".banner.ok", { timeout: 60000 });
  check(true, "upload do formulário bom: aprovado");

  // 3. Arquivo inválido
  const bogus = path.join(os.tmpdir(), "e2e_invalido.xlsx");
  fs.writeFileSync(bogus, "não é planilha");
  await page.setInputFiles("#arquivo", bogus);
  await page.waitForSelector(".banner.erro", { timeout: 60000 });
  check(/não parece ser uma planilha/.test(await page.textContent(".banner")), "arquivo inválido explicado ao usuário");

  // 4. Celular: sem rolagem horizontal
  const mobile = await browser.newPage({ viewport: { width: 375, height: 800 } });
  await mobile.goto(base);
  await mobile.waitForSelector('#status-motor[data-estado="pronto"]', { timeout: 180000 });
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
