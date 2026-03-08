function splitWords(str) {
  return str
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/[_\-]+/g, " ")
    .trim()
    .toLowerCase()
    .split(/\s+/);
}

export function pascalCase(str) {
  return splitWords(str)
    .map(function (w) {
      return w.charAt(0).toUpperCase() + w.slice(1);
    })
    .join("");
}

export function camelCase(str) {
  var s = pascalCase(str);
  return s.charAt(0).toLowerCase() + s.slice(1);
}

export function snakeCase(str) {
  return splitWords(str).join("_");
}
