import { formatAccessibilityTreeToYaml } from '../utils/yamlFormatter.js';

/**
 * Generates an accessibility snapshot for a given Puppeteer page.
 * @param {import('puppeteer').Page} page - The Puppeteer page object.
 * @param {string} [framePrefix='s1'] - The prefix for the root frame (e.g., 's1').
 * @returns {Promise<string>} - A promise that resolves with the YAML formatted accessibility snapshot.
 */
export async function generateAccessibilitySnapshot(page, framePrefix = 's1') {
  if (!page) {
    return 'Error: No page provided';
  }

  try {
    const accessibilityTree = await page.accessibility.snapshot({ interestingOnly: false });
    if (!accessibilityTree) {
      return 'Error: No accessibility tree available';
    }

    return formatAccessibilityTreeToYaml(accessibilityTree, framePrefix);
  } catch (error) {
    return `Error: ${error.message}`;
  }
}
