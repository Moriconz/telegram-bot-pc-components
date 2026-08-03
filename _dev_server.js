import { spawn } from 'child_process';
import { promisify } from 'util';

const exec = promisify(require('child_process').exec);

export default async function handler(req, res) {
  try {
    // Start Next.js dev server if not running
    const { stdout } = await exec('lsof -i :3000 2>/dev/null || echo "no"', { timeout: 3000 });
    if (!stdout.includes('3000')) {
      // Start dev server in background
      spawn('npx', ['next', 'dev', '-p', '3000'], {
        cwd: '/Users/riccardomoricone/telegram-bot-pc-components',
        detached: true,
        stdio: 'ignore'
      }).unref();
      await new Promise(r => setTimeout(r, 5000));
    }
    res.status(200).json({ message: 'Dev server started on port 3000' });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
}
