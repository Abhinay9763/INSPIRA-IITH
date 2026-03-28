REM Frontend Organization Commands
REM Run these commands in order

REM Step 1: Create directory structure
cd d:\Dev\Inpira_IITH\frontend
mkdir app
mkdir app\results
mkdir app\interview
mkdir app\debrief
mkdir lib
mkdir components

REM Step 2: Copy files from root to frontend
cd d:\Dev\Inpira_IITH

copy globals.css frontend\app\globals.css
copy app-layout.tsx frontend\app\layout.tsx
copy app-page.tsx frontend\app\page.tsx
copy results-app-page.tsx frontend\app\results\page.tsx
copy types.ts frontend\lib\types.ts
copy api.ts frontend\lib\api.ts
copy upload-form.tsx frontend\components\upload-form.tsx
copy progress-steps.tsx frontend\components\progress-steps.tsx
copy candidate-dossier.tsx frontend\components\candidate-dossier.tsx
copy score-card.tsx frontend\components\score-card.tsx
copy github-signals.tsx frontend\components\github-signals.tsx
copy signal-columns.tsx frontend\components\signal-columns.tsx
copy interview-threads.tsx frontend\components\interview-threads.tsx

REM Step 3: Move node_modules and clean up
move node_modules frontend\node_modules
move package-lock.json frontend\package-lock.json

REM Step 4: Delete files from root
del app-layout.tsx
del app-page.tsx
del results-app-page.tsx
del results-page.tsx
del layout.tsx
del page.tsx
del types.ts
del api.ts
del globals.css
del upload-form.tsx
del progress-steps.tsx
del candidate-dossier.tsx
del score-card.tsx
del github-signals.tsx
del signal-columns.tsx
del interview-threads.tsx
del next.config.js
del tailwind.config.js
del postcss.config.js
del tsconfig.json
del package.json
del .env.local

REM Step 5: Test the frontend
cd frontend
npm run dev