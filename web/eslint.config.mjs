import nextVitals from "eslint-config-next/core-web-vitals"
import nextTs from "eslint-config-next/typescript"

const ignoredPaths = [
  ".next/**",
  "node_modules/**",
  "next-env.d.ts",
]

const config = [
  { ignores: ignoredPaths },
  ...nextVitals,
  ...nextTs,
  {
    rules: {
      "react-hooks/set-state-in-effect": "off",
    },
  },
]

export default config
