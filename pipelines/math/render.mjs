import {createRequire} from 'node:module';
import {join} from 'node:path';
import {createInterface} from 'node:readline';

const require = createRequire(import.meta.url);
const root = join(process.argv[2], 'js');
const {mathjax} = require(join(root, 'mathjax.js'));
const {MathML} = require(join(root, 'input/mathml.js'));
const {SVG} = require(join(root, 'output/svg.js'));
const {liteAdaptor} = require(join(root, 'adaptors/liteAdaptor.js'));
const {RegisterHTMLHandler} = require(join(root, 'handlers/html.js'));
const adaptor = liteAdaptor();
RegisterHTMLHandler(adaptor);
const document = mathjax.document('', {
  InputJax: new MathML(), OutputJax: new SVG({fontCache: 'none'}),
  compileError: (_document, _math, error) => { throw error; },
  typesetError: (_document, _math, error) => { throw error; },
});
for await (const line of createInterface({input: process.stdin, crlfDelay: Infinity})) {
  try {
    const {mathml} = JSON.parse(line);
    if (typeof mathml !== 'string') throw new Error('MathML must be a string');
    const output = document.convert(mathml, {display: true});
    const svg = adaptor.firstChild(output);
    process.stdout.write(JSON.stringify({svg: adaptor.outerHTML(svg)}) + '\n');
  } catch (error) {
    process.stdout.write(JSON.stringify({error: String(error.message || error)}) + '\n');
  }
}
