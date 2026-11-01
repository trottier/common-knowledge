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

This development app needs Android {{ local_llm.android.minimum_android_version }} or newer and an {{ local_llm.android.abi }} phone. If it will not install or load, use START and the printed cards. [@offlinellm_build] [@project_spec]

1. Open **9_LOCAL_LLM → android → {{ local_llm.android.apk_filename }}**. Follow the phone's install prompts. Do not download a model or create an account. [@project_spec]
2. In {{ local_llm.android.app_name }}, open **Settings → Import GGUF Model**. Select **9_LOCAL_LLM → {{ local_llm.model_filename }}** on the drive, or a copy on your phone. Wait for the copy to finish. Stop if storage is full or import fails. [@offlinellm_import]
3. Tap **Use** beside that model if shown. In **Performance**, keep **GPU Acceleration (Vulkan)** {{ "on" if local_llm.android.gpu_acceleration else "off" }}. Set **CPU Threads** to {{ local_llm.threads }} if offered. If the needed controls are unavailable, use START. [@offlinellm_settings] [@project_spec]
4. In **Sampling Parameters**, set **Context Size** to {{ local_llm.android.context_tokens }} and **Max Tokens** to {{ local_llm.max_output_tokens }}. Set the **Temperature** display to {{ "%.2f" | format(local_llm.temperature) }}. [@offlinellm_settings] [@project_spec]
5. Under **System Prompt**, choose **Custom**. Open **9_LOCAL_LLM → android → system-en.txt** or **system-es.txt**. Copy the complete text into **Custom System Prompt**. Do not copy the laptop prompt from **ui**. [@offlinellm_settings] [@project_spec]
6. Return to the chat page and tap **New Chat**. Read START before acting. The Android prompt supplies only START section titles; it does not supply the full instructions. [@offlinellm_chat] [@project_spec]
7. Start a new chat if the app reports a full context or a model error. Do not shorten medical instructions to make them fit. If the problem continues, use START. [@project_spec]

Use text. Leave read-aloud controls off. If text will not work without downloading a font or voice, use START. [@project_spec]

{{ local_llm.warning }} [@project_spec]

[[VERIFY: check installation, exact controls, complete prompt paste, both selected GGUFs, readable text without downloaded fonts or voices, context errors, and offline behavior including delegated emoji-font and speech services on a phone with at least 6 GB RAM. Source, dependency-notice, and physical-device reviews remain open; no zero-traffic or model-quality claim.]]
