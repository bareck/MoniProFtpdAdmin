import { Page, ElementHandle } from 'puppeteer';

/**
 * Represents a node in the accessibility tree
 */
export interface AccessibilityNode {
  role: string;
  name?: string;
  value?: string;
  description?: string;
  properties?: Record<string, string>;
  selected?: boolean;
  checked?: boolean;
  disabled?: boolean;
  required?: boolean;
  focused?: boolean;
  level?: number;
  ref: string;
  children?: AccessibilityNode[];
}

/**
 * Generate a YAML-formatted accessibility snapshot from the current page
 * @param page Puppeteer page
 * @returns YAML string representation of the accessibility tree
 */
export async function generateAccessibilitySnapshot(page: Page): Promise<string> {
  const snapshot = await page.accessibility.snapshot();
  if (!snapshot) {
    return "- document [ref=s1e1]: No accessibility data available";
  }

  const processedSnapshot = processSnapshot(snapshot, 's1');
  return formatAsYaml(processedSnapshot);
}

/**
 * Process a raw accessibility node into a structured node with references
 * @param node Raw accessibility node from Puppeteer
 * @param refPrefix Reference prefix for this node
 * @param index Index for generating unique references
 * @returns Processed accessibility node
 */
function processSnapshot(node: any, refPrefix: string, index: number = 0): AccessibilityNode {
  // Process node and its children
  const ref = `${refPrefix}e${index + 1}`;
  const result: AccessibilityNode = {
    role: node.role || 'unknown',
    ref
  };

  // Add properties if they exist
  if (node.name) result.name = node.name;
  if (node.value) result.value = node.value;
  if (node.description) result.description = node.description;
  if (node.selected) result.selected = node.selected;
  if (node.checked) result.checked = node.checked;
  if (node.disabled) result.disabled = node.disabled;
  if (node.required) result.required = node.required;
  if (node.focused) result.focused = node.focused;

  // Handle heading level as a special case
  if (node.role === 'heading' && node.level) {
    result.level = node.level;
  }

  // Process children recursively with increased indentation
  if (node.children && node.children.length > 0) {
    result.children = node.children.map((child: any, idx: number) =>
      processSnapshot(child, ref, idx)
    );
  }

  return result;
}

/**
 * Format a processed accessibility node as YAML
 * @param node Processed accessibility node
 * @param indent Current indentation level
 * @returns YAML string representation
 */
function formatAsYaml(node: AccessibilityNode, indent: number = 0): string {
  const indentStr = '  '.repeat(indent);
  const lines: string[] = [];

  // Start with node role and name
  let line = `${indentStr}- ${node.role}`;

  // Add name if present (quoted)
  if (node.name) {
    line += ` "${escapeString(node.name)}"`;
  }

  // Add attributes in brackets
  const attributes: string[] = [];
  if (node.value) attributes.push(`value="${escapeString(node.value)}"`);
  if (node.selected) attributes.push('selected');
  if (node.checked) attributes.push('checked');
  if (node.disabled) attributes.push('disabled');
  if (node.required) attributes.push('required');
  if (node.focused) attributes.push('focused');
  if (node.level !== undefined) attributes.push(`level=${node.level}`);

  // Add ref at the end
  attributes.push(`ref=${node.ref}`);

  if (attributes.length > 0) {
    line += ` [${attributes.join('] [')}]`;
  }

  // Add colon if there are children
  if (node.children && node.children.length > 0) {
    line += ':';
  }

  lines.push(line);

  // Process children with increased indentation
  if (node.children && node.children.length > 0) {
    for (const child of node.children) {
      lines.push(formatAsYaml(child, indent + 1));
    }
  }

  return lines.join('\n');
}

/**
 * Escape special characters in strings for YAML
 * @param str String to escape
 * @returns Escaped string
 */
function escapeString(str: string): string {
  return str
    .replace(/\\/g, '\\\\')
    .replace(/"/g, '\\"')
    .replace(/\n/g, '\\n')
    .replace(/\r/g, '\\r')
    .replace(/\t/g, '\\t');
}
