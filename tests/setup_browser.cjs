// Created by Harsh Nair | Made in India | SPDX-License-Identifier: Apache-2.0
const { chromium, expect } = require('@playwright/test');
const { spawn } = require('node:child_process');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
(async () => {
  const server = spawn(path.join(root, '.venv/Scripts/python.exe'), [path.join(__dirname, 'setup_preview.py')], {windowsHide: true});
  let browser;
  try {
    const port = await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error('UI fixture startup timed out')), 10000);
      server.stdout.once('data', data => { clearTimeout(timeout); resolve(Number(data.toString().trim())); });
      server.once('error', reject);
    });
    browser = await chromium.launch({headless: true});
    const page = await browser.newPage({viewport: {width: 1020, height: 820}});
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(`http://127.0.0.1:${port}/setup`);
    const button = page.getByRole('button', {name: 'Set up storage and continue'});
    await expect(page.locator('#setup-progress')).toBeHidden();
    await button.click();
    await expect(button).toBeDisabled();
    await expect(page.locator('#setup-stage')).toHaveText('Checking PostgreSQL tools');
    await expect(page.locator('#setup-elapsed')).toContainText('Elapsed:');
    await page.screenshot({path: path.join(root, 'dist/setup-progress.png'), fullPage: true});
    await expect(page.locator('#setup-error')).toContainText('Test database could not start', {timeout: 10000});
    await expect(button).toBeEnabled();
    await button.click();
    await expect(page.locator('#setup-progress progress')).toBeVisible();
    await expect(page.locator('body')).toHaveText('Ready to import', {timeout: 10000});
    if (errors.length) throw new Error(errors.join('\n'));
    console.log('PASS: live progress, elapsed time, disabled duplicate submission, failure recovery, retry and successful navigation; no JavaScript errors.');
  } finally {
    if (browser) await browser.close();
    server.kill();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
