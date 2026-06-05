import js from "@eslint/js";

export default [
  js.configs.recommended,
  {
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      parserOptions: {
        ecmaFeatures: {
          jsx: true,
        },
      },
      globals: {
        window: "readonly",
        document: "readonly",
        console: "readonly",
        localStorage: "readonly",
        fetch: "readonly",
        setTimeout: "readonly",
        clearTimeout: "readonly",
        setInterval: "readonly",
        clearInterval: "readonly",
        HTMLDivElement: "readonly",
        HTMLElement: "readonly",
        MutationObserver: "readonly",
        DOMParser: "readonly",
        navigator: "readonly",
        matchMedia: "readonly",
        history: "readonly",
        location: "readonly",
        URLSearchParams: "readonly",
        Blob: "readonly",
        URL: "readonly",
        sessionStorage: "readonly",
        confirm: "readonly",
        prompt: "readonly",
        btoa: "readonly",
      },
    },
    rules: {
      "no-unused-vars": ["warn", { argsIgnorePattern: "^_" }],
      "no-undef": "error",
      "no-empty": ["error", { allowEmptyCatch: true }],
    },
  },
];
