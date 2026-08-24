# Kairozen Bot Hosting — Render Deploy Guide

## ១. Push ទៅ GitHub
```bash
git init
git add .
git commit -m "Prepare for Render deploy"
git branch -M main
git remote add origin https://github.com/sovannarinsorn-droid/<repo-name>.git
git push -u origin main
```

## ២. បង្កើត Service នៅ Render
1. ចូល https://dashboard.render.com → **New** → **Blueprint**
2. ភ្ជាប់ Repo នេះ — Render នឹងអាន `render.yaml` ដោយស្វ័យប្រវត្តិ (Background Worker + 1GB Persistent Disk mount នៅ `/data`)
3. Render នឹងសួររក Environment Variables ២ (ព្រោះកំណត់ `sync: false`):
   - `BOT_TOKEN` → Token ថ្មីពី @BotFather (**កុំប្រើ Token ចាស់ដែលធ្លាប់ Paste ក្នុង Chat នេះ — Revoke វាចោលមុន**)
   - `ADMIN_ID` → Telegram User ID របស់ Admin (លេខ, គ្មាន @)
4. ចុច **Apply** — Render នឹង Build និង Deploy ស្វ័យប្រវត្តិ

## ៣. ចំណុចសំខាន់
- Service ប្រភេទ **Background Worker** មិនមែន **Web Service** ទេ ព្រោះ Bot នេះប្រើ `infinity_polling`, គ្មាន HTTP Port
- `bot_database.db` និង `downloads/` (កូដ Bot របស់ User ដែល Host) ត្រូវរក្សាទុកនៅ `/data` (Persistent Disk) — បើគ្មាន Disk ទិន្នន័យនឹងបាត់រាល់ពេល Redeploy
- Plan `starter` ត្រូវការសម្រាប់ភ្ជាប់ Persistent Disk (Free plan មិនអាចមាន Disk)
- Bot ដែល User Host ខាងក្នុង (subprocess) នៅតែជា Python process — Render មិនកំណត់ port ណាមួយចាំបាច់ ព្រោះវាជា background worker
