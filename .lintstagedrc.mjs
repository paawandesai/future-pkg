const rel = (files, dir) => files.map((f) => f.slice(f.indexOf(`/${dir}/`) + dir.length + 2)).join(" ");

export default {
  "web/**/*.{ts,tsx,js,mjs,json,css,html}": (files) => [
    `pnpm --dir web exec prettier --write ${rel(files, "web")}`,
  ],
  "web/**/*.{ts,tsx,js,mjs}": (files) => [`pnpm --dir web exec eslint --max-warnings 0 ${rel(files, "web")}`],
  "api/**/*.py": (files) => [
    `uv run --project api --frozen -q ruff format ${files.join(" ")}`,
    `uv run --project api --frozen -q ruff check --fix ${files.join(" ")}`,
  ],
};
