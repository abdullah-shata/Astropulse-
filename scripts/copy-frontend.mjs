import { cpSync, mkdirSync, rmSync } from 'node:fs';
import { resolve } from 'node:path';

const source = resolve('5_frontend_hud/dist');
const destination = resolve('public');

rmSync(destination, { recursive: true, force: true });
mkdirSync(destination, { recursive: true });
cpSync(source, destination, { recursive: true });
