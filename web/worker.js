/* Executa o validador (Python) dentro do navegador, em segundo plano.
 *
 * Carrega o Pyodide e os pacotes Python servidos pelo próprio site. O arquivo do
 * usuário chega aqui por mensagem da página, é gravado no sistema de arquivos em
 * memória do Pyodide e nunca é enviado pela rede.
 *
 * Etapas informadas à página (mensagens "progress"):
 *   0 ambiente Python · 1 conversor oficial do XLSForm · 2 regras de qualidade
 */
importScripts("pyodide/pyodide.js");

let pyodide = null;
let validate = null;

function progress(step) {
  postMessage({ type: "progress", step });
}

async function fetchBytes(path) {
  const resp = await fetch(path);
  if (!resp.ok) throw new Error(`Falha ao baixar ${path} (${resp.status})`);
  return new Uint8Array(await resp.arrayBuffer());
}

async function init() {
  const t0 = performance.now();
  progress(0);
  // Os pacotes Python são baixados em paralelo com o ambiente Python.
  const files = fetch("manifest.json")
    .then((r) => r.json())
    .then((m) => [...m.wheels.map((w) => "wheels/" + w), "app.zip", "rules.json"]);
  const downloads = files.then((list) => Promise.all(list.map(fetchBytes)));
  downloads.catch(() => {}); // o erro é tratado quando o resultado é usado

  pyodide = await loadPyodide({ indexURL: "pyodide/" });

  progress(1);
  const list = await files;
  const data = await downloads;
  pyodide.FS.mkdirTree("/app");
  pyodide.FS.mkdirTree("/trabalho");
  list.forEach((f, i) => pyodide.FS.writeFile("/app/" + f.split("/").pop(), data[i]));
  pyodide.runPython(`
import glob, site, zipfile
dest = site.getsitepackages()[0]
for f in glob.glob('/app/*.whl') + ['/app/app.zip']:
    zipfile.ZipFile(f).extractall(dest)
import pyxform.xls2xform  # conversor oficial do XLSForm
`);

  progress(2);
  pyodide.runPython(`
from xlsform_validator.web import _configs, validate_for_web
_configs('/app/rules.json')
`);
  validate = pyodide.globals.get("validate_for_web");
  return Math.round(performance.now() - t0);
}

const ready = init().then(
  (ms) => postMessage({ type: "ready", ms }),
  (err) => postMessage({ type: "fatal", message: String(err) }),
);

function takeFile(path) {
  try {
    const bytes = pyodide.FS.readFile(path);
    pyodide.FS.unlink(path);
    return bytes;
  } catch {
    return null;
  }
}

onmessage = async (event) => {
  const { id, name, buffer } = event.data;
  const input = "/trabalho/formulario.xlsx";
  const annotatedPath = "/trabalho/anotado.xlsx";
  const readyPath = "/trabalho/pronto.xlsx";
  try {
    await ready;
    if (!validate) throw new Error("O validador não foi carregado.");
    pyodide.FS.writeFile(input, new Uint8Array(buffer));
    const json = validate(input, name, "/app/rules.json", annotatedPath, readyPath);
    const result = JSON.parse(json);
    const annotated = result.annotated ? takeFile(annotatedPath) : null;
    const readyFile = result.ready ? takeFile(readyPath) : null;
    takeFile(input);
    const transfer = [annotated, readyFile].filter(Boolean).map((b) => b.buffer);
    postMessage({ type: "result", id, json, annotated, ready: readyFile }, transfer);
  } catch (err) {
    postMessage({ type: "error", id, message: String(err) });
  }
};
