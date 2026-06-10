/**
 * Navigates to a new URL with updated URL parameters (`urlParams + delta`).
 */
export function navigateToUrl(urlParams, delta, location, navigate) {
  for (const key in delta) {
    if (delta[key] === null || delta[key] === false) {
      urlParams.delete(key);
    } else {
      urlParams.set(key, delta[key]);
    }
  }
  navigate({
    pathname: location.pathname,
    search: urlParams.toString(),
  });
}

/**
 * Returns the last element of an array.
 */
export function getLast(arr) {
  return arr[arr.length - 1];
}

/**
 * Return whether stack1 and stack2 refer to being in the same function (all but
 * the last element must agree).
 */
export function inSameFunction(stack1, stack2) {
  if (!stack1 || !stack2 || stack1.length !== stack2.length) {
    return false;
  }
  // Note: don't include the last element in the comparison
  for (let i = 0; i < stack1.length - 1; i++) {
    const a = stack1[i];
    const b = stack2[i];
    if (a.path !== b.path || a.line_number !== b.line_number) {
      return false;
    }
  }
  return true;
}

/**
 * Return whether stack1 is an ancestor of stack2.
 */
export function isStrictAncestorOf(stack1, stack2) {
  if (!stack1 || !stack2) return false;
  return stack1.length < stack2.length;
}

/**
 * Compute the merged environment for a given step index.
 *
 * Walks backward through steps in the same stack frame, collects their
 * env objects, and merges them (later steps overwrite earlier ones).
 *
 * Returns a plain object like `{ varName: value }`.
 */
export function computeEnv(trace, currentStepIndex) {
  const currentStep = trace.steps[currentStepIndex];
  if (!currentStep) return {};

  const envs = [];
  for (let stepIndex = currentStepIndex; stepIndex >= 0; stepIndex--) {
    const step = trace.steps[stepIndex];
    if (!step) continue;
    if (inSameFunction(step.stack, currentStep.stack)) {
      if (step.env && Object.keys(step.env).length > 0) {
        envs.push(step.env);
      }
    } else if (isStrictAncestorOf(step.stack, currentStep.stack)) {
      break;
    }
  }

  envs.reverse();

  const env = {};
  for (const stepEnv of envs) {
    Object.assign(env, stepEnv);
  }

  return env;
}

/**
 * Given a merged env object and the source file text, compute an array of
 * decoration objects `{ line, text }` suitable for passing to Editor's
 * `decorations` prop.
 *
 * Each decoration says what the current value of a variable is, placed on
 * the last source line where that variable name appears as an assignment.
 */
export function computeDecorations(env, source) {
  if (!env || Object.keys(env).length === 0) return [];
  if (!source) return [];

  const lines = source.split('\n');
  const decorations = [];

  for (const [varName, value] of Object.entries(env)) {
    // Find the last line in source where varName appears as an assignment
    // or type-annotation (e.g. `x = ...` or `x: int = ...`)
    let foundLine = 0;
    // Escape special regex characters in the variable name
    const escaped = varName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const pattern = new RegExp(`^\\s*${escaped}\\s*(=|:)`);
    for (let i = 0; i < lines.length; i++) {
      if (pattern.test(lines[i])) {
        foundLine = i + 1; // 1-based line numbers
      }
    }

    if (foundLine > 0) {
      const renderedValue = renderValue(value);
      decorations.push({
        line: foundLine,
        text: `${varName} = ${renderedValue}`,
      });
    }
  }

  return decorations;
}

/**
 * Format a JavaScript value as a compact inline string (no pretty-printing).
 */
function renderValue(value) {
  if (typeof value === 'number') {
    return String(value);
  }
  return JSON.stringify(value);
}