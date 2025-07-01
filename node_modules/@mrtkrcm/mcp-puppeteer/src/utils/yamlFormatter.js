import yaml from 'js-yaml';

const LAYOUT_ROLES = ['generic container', 'group', 'paragraph', 'list', 'listitem'];

/**
 * Converts an accessibility tree node to a simplified object for YAML.
 * @param {object} node - The accessibility tree node.
 * @param {string} prefix - The prefix for generating element IDs.
 * @param {number} index - The index of the node.
 * @returns {object | null} - Simplified node object or null.
 */
function simplifyNode(node, prefix, index) {
  if (!node.role && !node.name && !LAYOUT_ROLES.includes(node.role)) {
    return null;
  }

  const elementId = `${prefix}e${index + 1}`;
  const simplified = {
    id: elementId,
    role: node.role || 'unknown'
  };

  if (node.name) simplified.name = node.name;
  if (node.value) simplified.value = node.value;
  if (node.children?.length > 0) {
    const children = node.children
      .map((child, i) => simplifyNode(child, elementId, i))
      .filter(Boolean);
    if (children.length > 0) simplified.children = children;
  }

  return simplified;
}

/**
 * Formats an accessibility tree into a structured YAML string.
 * @param {object} accessibilityTree - The root node of the accessibility tree.
 * @param {string} framePrefix - Prefix indicating the frame.
 * @returns {string} - The formatted YAML string.
 */
export function formatAccessibilityTreeToYaml(accessibilityTree, framePrefix = 's1') {
  if (!accessibilityTree) return '';

  const simplifiedTree = simplifyNode(accessibilityTree, framePrefix, 0);
  if (!simplifiedTree) return '';

  try {
    return yaml.dump(simplifiedTree, {
      indent: 2,
      noRefs: true,
      lineWidth: -1
    });
  } catch (error) {
    throw new Error(`YAML formatting failed: ${error.message}`);
  }
}
