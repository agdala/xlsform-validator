/* Executa o validador (Python) dentro do navegador, em segundo plano.
 *
 * Carrega o Pyodide e os pacotes Python servidos pelo próprio site. O arquivo do
 * usuário chega aqui por mensagem da página, é gravado no sistema de arquivos em
 * memória do Pyodide e nunca é enviado pela rede.
 */
importScripts("pyodide/pyodide.js");

let pyodide = null;
let validate = null;

async function fetchBytes(path) {
  const resp = await fetch(path);
  if (!resp.ok) throw new Error(`Falha ao baixar ${path} (${resp.status})`);
  return new Uint8Array(await resp.arrayBuffer());
}

async function init() {
  const t0 = performance.now();
  pyodide = await loadPyodide({ indexURL: "pyodide/" });
  const manifest = await (await fetch("manifest.json")).json();
  const files = [...manifest.wheels.map((w) => "wheels/" + w), "app.zip", "rules.json"];
  pyodide.FS.mkdirTree("/app");
  pyodide.FS.mkdirTree("/trabalho");
  const downloads = await Promise.all(files.map(fetchBytes));
  files.forEach((f, i) => pyodide.FS.writeFile("/app/" + f.split("/").pop(), downloads[i]));
  pyodide.runPython(`
import glob, site, zipfile
dest = site.getsitepackages()[0]
for f in glob.glob('/app/*.whl') + ['/app/app.zip']:
    zipfile.ZipFile(f).extractall(dest)
from xlsform_validator.web import _configs, validate_for_web
_configs('/app/rules.json')  # importa pyxform e regras agora, para a 1ª validação ser rápida
`);
  validate = pyodide.globals.get("validate_for_web");
  return Math.round(performance.now() - t0);
}

const ready = init().then(
  (ms) => postMessage({ type: "ready", ms }),
  (err) => postMessage({ type: "fatal", message: String(err) }),
);

onmessage = async (event) => {
  const { id, name, buffer } = event.data;
  const input = "/trabalho/formulario.xlsx";
  const output = "/trabalho/anotado.xlsx";
  try {
    await ready;
    if (!validate) throw new Error("O validador não foi carregado.");
    pyodide.FS.writeFile(input, new Uint8Array(buffer));
    const json = validate(input, name, "/app/rules.json", output);
    let annotated = null;
    if (JSON.parse(json).annotated) {
      annotated = pyodide.FS.readFile(output);
      pyodide.FS.unlink(output);
    }
    pyodide.FS.unlink(input);
    postMessage({ type: "result", id, json, annotated }, annotated ? [annotated.buffer] : []);
  } catch (err) {
    postMessage({ type: "error", id, message: String(err) });
  }
};
