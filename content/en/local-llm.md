---
title: Open the local LLM
status: draft
reviewer: null
reviewed_on: null
---

{{ local_llm.warning }} [@project_spec]

## Laptop

Open **9_LOCAL_LLM**. Open **Start Local LLM** for your system: Windows, Mac or Linux. Keep the drive connected. The launcher opens a page in your browser. [@project_spec]

Choose **English** or **Español** for the START text. Type a short question. Read the START section named in the answer before acting. [@project_spec]

Keep the launcher's window open while you use it. Close that window to stop. If it fails, use START and the printed cards. [@project_spec]

[[VERIFY: check double-click opening and the full offline flow on Windows, Mac and Linux, including a USB-A-only laptop with an adapter]]

## Android — optional

Open **9_LOCAL_LLM → android → PocketPal.apk**. Follow your phone's install prompts. [@project_spec]

[[VERIFY: test APK installation and local model import on a phone with at least 6 GB RAM]]

In PocketPal, open **Menu → Models → +**. Choose a file from local storage. Select **9_LOCAL_LLM → Model.gguf** on the drive, or a copy on your phone. Load the model. [@pocketpal_local]

Open the **Chat** page. Keep START beside it. For the project instructions, create an **Assistant Pal** and copy the text from **ui → system-en.txt** or **system-es.txt** into its system prompt. [@pocketpal_local]

[[VERIFY: test the exact model picker and system-prompt flow in the pinned APK with networking off]]

Use the local file. Do not use model downloads or online tools during an outage. If the app cannot open it, use START. [@project_spec]
