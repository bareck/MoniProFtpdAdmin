/**
 * Parses an element reference ID into its components.
 * Format: f{frameIndex}s{snapshotIndex}e{elementIndex} or s{snapshotIndex}e{elementIndex}
 * @param {string} refId - Element reference ID (e.g., 'f0s1e2' or 's1e2')
 * @returns {{ frameIndex?: number, snapshotIndex: number, elementIndex: number }}
 * @throws {Error} If the reference ID format is invalid
 */
export function parseElementRefId(refId) {
  const frameMatch = refId.match(/^f(\d+)s(\d+)e(\d+)$/);
  if (frameMatch) {
    return {
      frameIndex: parseInt(frameMatch[1], 10),
      snapshotIndex: parseInt(frameMatch[2], 10),
      elementIndex: parseInt(frameMatch[3], 10)
    };
  }

  const mainMatch = refId.match(/^s(\d+)e(\d+)$/);
  if (mainMatch) {
    return {
      snapshotIndex: parseInt(mainMatch[1], 10),
      elementIndex: parseInt(mainMatch[2], 10)
    };
  }

  throw new Error(`Invalid element reference ID format: ${refId}`);
}

/**
 * Finds an element in the accessibility tree by its role.
 * @param {object} tree - The accessibility tree to search
 * @param {string} refId - Element reference ID (used for error context)
 * @param {string} [targetRole] - Role to match (e.g., 'button')
 * @returns {object | null} The found element or null if not found
 */
export function findElementByRefId(tree, refId, targetRole = null) {
  if (!tree || !refId) return null;

  // Traverse the tree to find the target element
  function traverse(node) {
    if (!node) return null;

    // Check if this node matches the target role
    if (targetRole && node.role?.toLowerCase() === targetRole.toLowerCase()) {
      return node;
    }

    // If no target role specified, return any top-level interactive element
    if (!targetRole && isInteractiveElement(node)) {
      return node;
    }

    // Recursively check children
    if (node.children && node.children.length > 0) {
      for (const child of node.children) {
        const result = traverse(child);
        if (result) return result;
      }
    }
    return null;
  }

  return traverse(tree);
}

/**
 * Check if a node is an interactive element
 * @param {object} node - Node from the accessibility tree
 * @returns {boolean} True if interactive
 */
function isInteractiveElement(node) {
  const interactiveRoles = [
    'button', 'link', 'checkbox', 'combobox', 'menuitem',
    'menuitemcheckbox', 'menuitemradio', 'option', 'radio',
    'scrollbar', 'searchbox', 'slider', 'spinbutton', 'switch',
    'tab', 'textbox', 'treeitem'
  ];

  return node && node.role && interactiveRoles.includes(node.role.toLowerCase());
}

/**
 * Finds an element in a page by its reference ID, handling frames.
 * @param {import('puppeteer').Page} page - Puppeteer page object
 * @param {string} refId - Element reference ID
 * @returns {Promise<{ frame: import('puppeteer').Frame, element: object } | null>} Frame and element if found
 */
export async function findElementInPage(page, refId) {
  if (!page || !refId) return null;

  const ref = parseElementRefId(refId);

  try {
    // Get all frames
    const frames = await page.frames();

    // Get the target frame
    let targetFrame;
    if (ref.frameIndex !== undefined && ref.frameIndex < frames.length) {
      targetFrame = frames[ref.frameIndex];
    } else {
      targetFrame = page.mainFrame();
    }

    // Make sure frame is loaded
    await targetFrame.waitForSelector('*', { timeout: 2000 }).catch(() => null);

    // Get accessibility tree for the frame
    const tree = await targetFrame.accessibility.snapshot({ interestingOnly: false });
    if (!tree) return null;

    // First try to find a button element
    let element = findElementByRefId(tree, refId, 'button');

    // If no button found, try any element
    if (!element) {
      element = findElementByRefId(tree, refId);
    }

    return element ? { frame: targetFrame, element } : null;
  } catch (error) {
    console.error(`Error finding element: ${error.message}`);
    return null;
  }
}

/**
 * Gets all frames in a page with their accessibility trees.
 * @param {import('puppeteer').Page} page - Puppeteer page object
 * @returns {Promise<Array<{ frame: import('puppeteer').Frame, tree: object }>>}
 */
export async function getAllFrameTrees(page) {
  if (!page) return [];

  const frames = await page.frames();
  const results = await Promise.allSettled(frames.map(async frame => {
    const tree = await frame.accessibility.snapshot({ interestingOnly: false });
    return { frame, tree };
  }));

  return results
    .filter(result => result.status === 'fulfilled')
    .map(result => result.value)
    .filter(({ tree }) => tree !== null);
}
