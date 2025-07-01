import puppeteer, { Browser, Page } from 'puppeteer';
import { getBrowserConfig } from './browserConfig.js';

/**
 * Connect to a browser with retry logic
 * @param endpoint WebSocket endpoint
 * @param maxRetries Maximum number of retries
 * @returns Connected browser instance
 */
export async function connectWithRetry(endpoint: string, maxRetries = 3): Promise<Browser> {
  let retries = 0;
  let lastError: Error | undefined;

  while (retries <= maxRetries) {
    try {
      console.error(`Connection attempt ${retries + 1}/${maxRetries + 1} to ${endpoint}`);
      const browser = await puppeteer.connect({
        browserWSEndpoint: endpoint,
        protocolTimeout: 30000
      });
      return browser;
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error));
      console.error(`Connection attempt ${retries + 1} failed: ${lastError.message}`);

      if (retries < maxRetries) {
        // Exponential backoff
        const delay = Math.pow(2, retries) * 1000;
        console.error(`Retrying in ${delay}ms...`);
        await new Promise(resolve => setTimeout(resolve, delay));
      }

      retries++;
    }
  }

  throw lastError || new Error('Failed to connect to browser after retries');
}

/**
 * Set up event handlers for a page to capture errors and logs
 * @param page Puppeteer page
 * @param logs Array to store logs
 */
export function setupPageErrorHandlers(page: Page, logs: string[]): void {
  // Console messages
  page.on('console', msg => {
    const logEntry = `[${msg.type()}] ${msg.text()}`;
    logs.push(logEntry);
  });

  // Page errors
  page.on('pageerror', error => {
    logs.push(`[ERROR] Page error: ${error.message}`);
  });

  // Request failures
  page.on('requestfailed', request => {
    logs.push(`[NETWORK] Request failed: ${request.url()} - ${request.failure()?.errorText || 'Unknown error'}`);
  });

  // Response errors (status >= 400)
  page.on('response', response => {
    const status = response.status();
    if (status >= 400) {
      logs.push(`[NETWORK] Response error: ${response.url()} - Status ${status}`);
    }
  });
}

/**
 * Create a new page with default configuration
 * @param browser Browser instance
 * @returns Configured page
 */
export async function createPage(browser: Browser): Promise<Page> {
  const page = await browser.newPage();
  const config = getBrowserConfig();

  // Apply viewport if specified
  if (config.defaultViewport) {
    await page.setViewport(config.defaultViewport);
  }

  // Apply user agent if specified
  if (config.userAgent) {
    await page.setUserAgent(config.userAgent);
  }

  return page;
}
