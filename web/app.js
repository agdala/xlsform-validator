/* Interface do validador. Toda a validação acontece no worker.js, no navegador. */
"use strict";

const GROUP_ORDER = [
  "Estrutura", "Nomes de variáveis", "Listas de opções", "Lógica", "Validações",
  "Metadados de coleta", "Consentimento", "Proteção de dados (LGPD)", "Desagregação",
  "Idiomas", "Validação técnica (pyxform)",
];
const STATUS = {
  aprovado: { cls: "ok", titulo: "Aprovado", texto: "O formulário segue o padrão de qualidade e está pronto para publicar." },
  aprovado_com_avisos: { cls: "aviso", titulo: "Aprovado com avisos", texto: "Não há erros: o formulário pode ser publicado. Os avisos são recomendações para melhorar a qualidade dos dados e não impedem a publicação." },
  reprovado: { cls: "erro", titulo: "Reprovado", texto: "Corrija os erros antes de publicar. Os avisos são recomendações." },
  ilegivel: { cls: "erro", titulo: "Não foi possível ler o arquivo", texto: "Confira se é uma planilha .xlsx válida (no Kobo: Download XLS)." },
};

const $ = (sel) => document.querySelector(sel);
const worker = new Worker("worker.js");
let ready = false;
let pending = null;
let requestId = 0;
let lastResult = null;
let filter = "todos";

/* Cria elementos sem innerHTML: o conteúdo da planilha nunca é interpretado como HTML. */
function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === null || value === undefined || value === false) continue;
    if (key === "class") node.className = value;
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else node.setAttribute(key, value === true ? "" : value);
  }
  for (const child of children.flat()) {
    if (child === null || child === undefined || child === false) continue;
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

function plural(n, um, varios) {
  return `${n} ${n === 1 ? um : varios}`;
}

/* ------------------------------------------------------------------ motor */

const STEP_TARGET = [8, 55, 90, 100]; // % da barra ao concluir cada etapa (estimativa)
const loadStart = performance.now();
let currentStep = 0;
let stepStart = loadStart;
let barValue = 0;
const loadTimer = setInterval(tickLoading, 250);

function tickLoading() {
  const elapsed = (performance.now() - loadStart) / 1000;
  $("#carga-tempo").textContent = `${Math.floor(elapsed)} s`;
  // Avança devagar dentro da etapa atual, sem chegar ao marco da próxima.
  const from = currentStep === 0 ? 0 : STEP_TARGET[currentStep - 1];
  const to = STEP_TARGET[currentStep] - 2;
  const inStep = (performance.now() - stepStart) / 1000;
  const value = from + (to - from) * (1 - Math.exp(-inStep / 6));
  setBar(Math.max(barValue, value));
}

function setBar(value) {
  barValue = value;
  $("#barra").style.width = `${value.toFixed(1)}%`;
}

function setStep(step) {
  currentStep = step;
  stepStart = performance.now();
  setBar(step === 0 ? barValue : Math.max(barValue, STEP_TARGET[step - 1]));
  document.querySelectorAll("#etapas li").forEach((li) => {
    const n = Number(li.dataset.etapa);
    li.dataset.status = n < step ? "feito" : n === step ? "atual" : "pendente";
  });
}

function setEnabled(enabled) {
  const zone = $("#zona-envio");
  zone.classList.toggle("desabilitada", !enabled);
  zone.setAttribute("aria-disabled", enabled ? "false" : "true");
  $("#arquivo").disabled = !enabled;
  document.querySelectorAll("[data-exemplo]").forEach((b) => (b.disabled = !enabled));
}

function rememberVisit() {
  try {
    localStorage.setItem("xlsform-validator:carregou", "1");
  } catch {}
}

try {
  if (localStorage.getItem("xlsform-validator:carregou")) {
    $("#carga-dica").textContent =
      "Você já usou o validador neste navegador: os arquivos guardados costumam deixar o carregamento mais rápido.";
  }
} catch {}

setStep(0);

worker.onmessage = (event) => {
  const msg = event.data;
  if (msg.type === "progress") {
    setStep(msg.step);
  } else if (msg.type === "ready") {
    ready = true;
    clearInterval(loadTimer);
    setStep(3);
    setBar(100);
    const seconds = Math.max(1, Math.round(msg.ms / 1000));
    $("#carga").dataset.estado = "pronto";
    $("#carga-titulo").textContent = `Validador pronto (carregado em ${seconds} s). Envie um arquivo.`;
    setEnabled(true);
    rememberVisit();
    if (pending) {
      const job = pending;
      pending = null;
      runValidation(job.name, job.buffer);
    }
  } else if (msg.type === "fatal") {
    clearInterval(loadTimer);
    $("#carga").dataset.estado = "falha";
    $("#carga-titulo").textContent =
      "Não foi possível carregar o validador neste navegador. Atualize a página ou tente outro navegador (Chrome, Edge, Firefox ou Safari atualizados).";
    console.error(msg.message);
  } else if (msg.type === "result" && msg.id === requestId) {
    showResult(JSON.parse(msg.json), msg.annotated, msg.ready);
  } else if (msg.type === "error" && msg.id === requestId) {
    showFailure(msg.message);
  }
};

/* ------------------------------------------------------------------ envio */

async function handleFile(file) {
  if (!file || !ready) return;
  if (!/\.xlsx$/i.test(file.name)) {
    showFailure("Envie uma planilha no formato .xlsx. Se o arquivo for .xls (antigo), abra no Excel e salve como .xlsx.");
    return;
  }
  validateBuffer(file.name, await file.arrayBuffer());
}

function validateBuffer(name, buffer) {
  showLoading(name);
  if (!ready) {
    pending = { name, buffer };
    return;
  }
  runValidation(name, buffer);
}

function runValidation(name, buffer) {
  requestId += 1;
  worker.postMessage({ id: requestId, name, buffer }, [buffer]);
}

const input = $("#arquivo");
const zone = $("#zona-envio");
input.addEventListener("change", () => {
  handleFile(input.files[0]);
  input.value = "";
});
["dragenter", "dragover"].forEach((type) =>
  zone.addEventListener(type, (e) => {
    e.preventDefault();
    zone.classList.add("arrastando");
  }),
);
["dragleave", "drop"].forEach((type) =>
  zone.addEventListener(type, (e) => {
    e.preventDefault();
    zone.classList.remove("arrastando");
  }),
);
zone.addEventListener("drop", (e) => {
  if (ready) handleFile(e.dataTransfer.files[0]);
});

document.querySelectorAll("[data-exemplo]").forEach((button) =>
  button.addEventListener("click", async () => {
    const path = button.dataset.exemplo;
    const resp = await fetch(path);
    validateBuffer(path.split("/").pop(), await resp.arrayBuffer());
  }),
);

/* ------------------------------------------------------------------ resultado */

function resultSection() {
  const section = $("#resultado");
  section.hidden = false;
  section.replaceChildren();
  return section;
}

function showLoading(name) {
  const section = resultSection();
  section.append(
    el("div", { class: "cartao carregando" },
      el("span", { class: "spinner", "aria-hidden": "true" }),
      el("span", {}, ready ? `Validando ${name}…` : `Validando ${name}. Aguarde o validador terminar de carregar…`),
    ),
  );
  section.scrollIntoView({ behavior: "smooth", block: "start" });
}

function showFailure(message) {
  const section = resultSection();
  section.append(
    el("div", { class: "banner erro" },
      el("div", {},
        el("h2", {}, "Algo deu errado"),
        el("p", {}, message),
      ),
    ),
  );
}

function download(name, data, type) {
  const blob = new Blob([data], { type });
  const url = URL.createObjectURL(blob);
  const a = el("a", { href: url, download: name });
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function baseName(file) {
  return file.replace(/\.xlsx$/i, "");
}

function showResult(result, annotated, readyFile) {
  lastResult = { result, annotated, readyFile };
  filter = "todos";
  render();
}

function render() {
  const { result, annotated, readyFile } = lastResult;
  const report = result.report;
  const status = STATUS[report.status] || STATUS.reprovado;
  const section = resultSection();

  const counts = report.read_error
    ? report.read_error
    : `${plural(report.summary.errors, "erro", "erros")} e ${plural(report.summary.warnings, "aviso", "avisos")}`;

  section.append(
    el("div", { class: `banner ${status.cls}` },
      el("div", { class: "banner-icone", "aria-hidden": "true" }, status.cls === "ok" ? "✓" : status.cls === "aviso" ? "!" : "✕"),
      el("div", {},
        el("p", { class: "banner-arquivo" }, report.file),
        el("h2", {}, `${status.titulo}${report.read_error ? "" : `: ${counts}`}`),
        el("p", {}, report.read_error ? counts : status.texto),
      ),
    ),
  );

  if (report.read_error) return;

  const xlsxType = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
  const base = baseName(report.file).replace(/_anotado$/, "");
  const approved = report.summary.errors === 0;
  const warnings = report.summary.warnings;
  const actions = el("div", { class: "acoes" });
  const annotatedButton = (primary) =>
    el("button", {
      type: "button", class: primary ? "botao primario" : "botao",
      onclick: () => download(`${base}_anotado.xlsx`, annotated, xlsxType),
    }, primary ? "Baixar planilha anotada (.xlsx)" : warnings ? "Planilha anotada com os avisos (.xlsx)" : "Planilha anotada (.xlsx)");

  if (approved && readyFile) {
    actions.append(
      el("button", {
        type: "button", class: "botao primario", "data-acao": "pronto",
        onclick: () => download(`${base}_pronto.xlsx`, readyFile, xlsxType),
      }, "Baixar formulário pronto para publicar (.xlsx)"),
    );
    if (annotated) actions.append(annotatedButton(false));
  } else if (annotated) {
    actions.append(annotatedButton(true));
  }
  actions.append(
    el("button", {
      type: "button", class: "botao",
      onclick: () => download(`relatorio_${base}.md`, result.markdown, "text/markdown"),
    }, "Relatório (.md)"),
    el("button", {
      type: "button", class: "botao",
      onclick: () => download(`relatorio_${base}.json`, JSON.stringify(report, null, 2), "application/json"),
    }, "Dados (.json)"),
    el("button", {
      type: "button", class: "botao-link",
      onclick: () => { $("#zona-envio").scrollIntoView({ behavior: "smooth" }); $("#arquivo").focus(); },
    }, "Validar outro arquivo"),
  );
  section.append(actions);

  let help;
  if (approved && readyFile) {
    help = result.ready_cleaned
      ? "O formulário pronto é o seu arquivo sem a aba ‘validacao’, as cores e os comentários de uma validação anterior. Pode subir direto no KoboToolbox, ODK, SurveyCTO, Ona ou ArcGIS Survey123."
      : "O formulário pronto é o seu arquivo original, sem nenhuma alteração. Pode subir direto no KoboToolbox, ODK, SurveyCTO, Ona ou ArcGIS Survey123.";
    if (warnings) {
      help += warnings === 1
        ? " O aviso abaixo é uma recomendação: vale revisar, mas não impede a publicação. A planilha anotada mostra onde ele está."
        : ` Os ${warnings} avisos abaixo são recomendações: vale revisar, mas não impedem a publicação. A planilha anotada mostra onde cada um está.`;
    }
  } else if (annotated) {
    help = "Na planilha anotada, as linhas com problema ficam coloridas (vermelho para erro, amarelo para aviso) e a célula mais escura tem um comentário com o que corrigir. A primeira aba, ‘validacao’, resume tudo com links. Corrija os erros e valide de novo: quando o formulário for aprovado, a página oferece o arquivo pronto para publicar, sem as marcações.";
  }
  if (help) section.append(el("p", { class: "texto-apoio", id: "ajuda-download" }, help));
  if (result.note) section.append(el("p", { class: "nota" }, result.note));

  const failed = report.rules.filter((r) => !r.passed);
  const passed = report.rules.filter((r) => r.passed);

  if (failed.length) {
    const total = report.summary.errors + report.summary.warnings;
    const chips = el("div", { class: "filtros", role: "group", "aria-label": "Filtrar problemas" },
      chip("todos", `Todos (${total})`),
      chip("erro", `Erros (${report.summary.errors})`),
      chip("aviso", `Avisos (${report.summary.warnings})`),
    );
    section.append(chips);

    const visible = failed.filter((r) => filter === "todos" || r.severity === filter);
    const groups = groupBy(visible, (r) => r.group);
    for (const group of sortGroups(Object.keys(groups))) {
      const rules = groups[group].sort((a, b) => (a.severity === b.severity ? a.rule_id.localeCompare(b.rule_id) : a.severity === "erro" ? -1 : 1));
      section.append(
        el("div", { class: "grupo" },
          el("h3", {}, group),
          rules.map(ruleCard),
        ),
      );
    }
    if (!visible.length) section.append(el("p", { class: "texto-apoio" }, "Nenhum item neste filtro."));
  }

  if (passed.length) {
    section.append(
      el("details", { class: "aprovadas" },
        el("summary", {}, `${plural(passed.length, "verificação aprovada", "verificações aprovadas")}`),
        el("ul", {}, passed.map((r) => el("li", {}, el("span", { class: "id-regra" }, r.rule_id), " ", r.description))),
      ),
    );
  }
}

function chip(value, label) {
  return el("button", {
    type: "button",
    class: `chip${filter === value ? " ativo" : ""}`,
    "aria-pressed": filter === value ? "true" : "false",
    onclick: () => { filter = value; render(); },
  }, label);
}

function ruleCard(rule) {
  const sev = rule.severity === "erro" ? "erro" : "aviso";
  return el("details", { class: `regra ${sev}`, open: true },
    el("summary", {},
      el("span", { class: `pilula ${sev}` }, sev === "erro" ? "Erro" : "Aviso"),
      el("span", { class: "regra-titulo" }, rule.description),
      el("span", { class: "regra-meta" }, `${rule.rule_id} · ${plural(rule.findings.length, "ocorrência", "ocorrências")}`),
    ),
    el("p", { class: "porque" }, el("strong", {}, "Por que importa: "), rule.why_it_matters),
    el("ul", { class: "ocorrencias" }, rule.findings.map(findingItem)),
  );
}

function findingItem(f) {
  const where = f.sheet ? (f.row ? `${f.sheet} · linha ${f.row}` : f.sheet) : "formulário";
  const message = f.message.replace(/^pyxform: /, "Conversor oficial: ");
  const fix = f.suggestion || "";
  const isOriginal = fix.startsWith("Mensagem original:");
  return el("li", {},
    el("span", { class: "local" }, where),
    el("div", {},
      el("p", { class: "mensagem" }, message),
      fix && !isOriginal ? el("p", { class: "correcao" }, el("strong", {}, "Como corrigir: "), fix) : null,
      isOriginal ? el("details", { class: "original" }, el("summary", {}, "Ver mensagem original em inglês"), el("p", {}, fix.replace("Mensagem original: ", ""))) : null,
    ),
  );
}

function groupBy(list, key) {
  return list.reduce((acc, item) => {
    (acc[key(item)] ||= []).push(item);
    return acc;
  }, {});
}

function sortGroups(groups) {
  const pos = (g) => (GROUP_ORDER.indexOf(g) === -1 ? 99 : GROUP_ORDER.indexOf(g));
  return groups.sort((a, b) => pos(a) - pos(b));
}

/* ------------------------------------------------------------------ lista de regras */

fetch("rules.json")
  .then((r) => r.json())
  .then((data) => {
    const rules = Object.entries(data.regras).map(([id, r]) => ({ id, ...r }));
    const groups = groupBy(rules, (r) => r.grupo);
    const box = $("#lista-regras");
    for (const group of sortGroups(Object.keys(groups))) {
      box.append(
        el("details", {},
          el("summary", {}, `${group} (${groups[group].length})`),
          el("ul", {}, groups[group].map((r) =>
            el("li", {},
              el("span", { class: `pilula ${r.severidade}` }, r.severidade === "erro" ? "Erro" : "Aviso"),
              " ",
              el("span", { class: "id-regra" }, r.id),
              " ",
              r.descricao,
              r.ativa === false ? el("em", {}, " (só na versão de linha de comando)") : null,
            ),
          )),
        ),
      );
    }
  })
  .catch(() => {});
