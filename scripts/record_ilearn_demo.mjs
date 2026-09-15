/**
 * Continuous ILearn demo recorder (replaces look-demo multi-scene output).
 *
 * look-demo restarts FFmpeg per scene and overwrites the same mp4, so only
 * the last scene survives. This script records one continuous Playwright video.
 *
 * Usage (repo root, FE+BE already up):
 *   node scripts/record_ilearn_demo.mjs
 */
import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..');
const SCRIPT_PATH = path.join(ROOT, 'doc', 'submit', 'look-demo-script.json');
const OUT_DIR = path.join(ROOT, 'runtime_evidence');
const SHOT_DIR = path.join(OUT_DIR, 'demo_screenshots');
const TMP_DIR = path.join(OUT_DIR, '_tmp_playwright_video');
const OUT_MP4 = path.join(OUT_DIR, 'demo_recording.mp4');
const WIDTH = 1920;
const HEIGHT = 1080;

function run(cmd, args) {
  return new Promise((resolve, reject) => {
    const child = spawn(cmd, args, { stdio: 'inherit', shell: process.platform === 'win32' });
    child.on('error', reject);
    child.on('close', (code) => (code === 0 ? resolve() : reject(new Error(`${cmd} exited ${code}`))));
  });
}

async function sleep(ms) {
  await new Promise((r) => setTimeout(r, ms));
}

async function runAction(page, action) {
  switch (action.type) {
    case 'wait':
      await sleep((action.duration || 1) * 1000);
      break;
    case 'click':
      if (action.selector) {
        try {
          await page.click(action.selector, { timeout: 8000 });
        } catch {
          console.warn(`  click miss: ${action.selector}`);
        }
      }
      break;
    case 'scroll': {
      const amount = action.direction === 'up' ? -(action.amount || 300) : action.amount || 300;
      await page.evaluate((y) => window.scrollBy({ top: y, behavior: 'smooth' }), amount);
      await sleep(600);
      break;
    }
    case 'hover':
      if (action.selector) {
        try {
          await page.hover(action.selector, { timeout: 5000 });
        } catch {
          console.warn(`  hover miss: ${action.selector}`);
        }
      }
      break;
    case 'screenshot': {
      const destRaw =
        action.path ||
        (action.name
          ? path.join(SHOT_DIR, action.name.endsWith('.png') ? action.name : `${action.name}.png`)
          : null);
      if (destRaw) {
        const dest = path.isAbsolute(destRaw) ? destRaw : path.join(ROOT, destRaw);
        fs.mkdirSync(path.dirname(dest), { recursive: true });
        await page.screenshot({ path: dest, fullPage: false });
        console.log(`  shot -> ${path.relative(ROOT, dest)}`);
      }
      break;
    }
    case 'goto':
      if (action.url) {
        await page.goto(action.url, { waitUntil: 'networkidle', timeout: 30000 });
      }
      break;
    default:
      break;
  }
}

async function main() {
  const { scenes } = JSON.parse(fs.readFileSync(SCRIPT_PATH, 'utf8'));
  fs.mkdirSync(SHOT_DIR, { recursive: true });
  fs.rmSync(TMP_DIR, { recursive: true, force: true });
  fs.mkdirSync(TMP_DIR, { recursive: true });

  console.log(`Recording ${scenes.length} scenes continuously -> ${path.relative(ROOT, OUT_MP4)}`);

  const browser = await chromium.launch({
    headless: true,
    args: [`--window-size=${WIDTH},${HEIGHT}`],
  });
  const context = await browser.newContext({
    viewport: { width: WIDTH, height: HEIGHT },
    recordVideo: { dir: TMP_DIR, size: { width: WIDTH, height: HEIGHT } },
  });
  const page = await context.newPage();

  try {
    for (let i = 0; i < scenes.length; i++) {
      const scene = scenes[i];
      const started = Date.now();
      console.log(`\n[${i + 1}/${scenes.length}] ${scene.name}`);

      if (scene.url) {
        await page.goto(scene.url, { waitUntil: 'networkidle', timeout: 30000 });
        await sleep(800);
      }

      for (const action of scene.actions || []) {
        await runAction(page, action);
        await sleep(120);
      }

      const targetMs = Math.max((scene.duration || 5) * 1000, 2500);
      const remain = targetMs - (Date.now() - started);
      if (remain > 0) {
        console.log(`  hold ${Math.round(remain / 1000)}s`);
        await sleep(remain);
      }
    }
  } finally {
    await context.close();
    await browser.close();
  }

  const webm = fs.readdirSync(TMP_DIR).find((f) => f.endsWith('.webm'));
  if (!webm) throw new Error('Playwright did not produce a .webm');
  const webmPath = path.join(TMP_DIR, webm);

  console.log('\nTranscoding webm -> mp4 via ffmpeg...');
  await run('ffmpeg', [
    '-y',
    '-i',
    webmPath,
    '-c:v',
    'libx264',
    '-pix_fmt',
    'yuv420p',
    '-movflags',
    '+faststart',
    '-crf',
    '23',
    OUT_MP4,
  ]);

  fs.rmSync(TMP_DIR, { recursive: true, force: true });
  console.log(`Done: ${OUT_MP4}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
