# SpiderNet V2 — Context Log

- **Última acción realizada:** Proyecto inicial cerrado: CLI, parseo de objetivos, chequeo de 7 plataformas, recursión resiliente, árbol `rich` y guardado inmediato en JSON.
- **Cómo se ha implementado:** `modules/platform_check.py` extrae el username de handles y URLs (TikTok `@user`, GitHub, YouTube, Reddit `/user/`, etc.). `core/spider.py` rota User-Agents de PC/móvil, mantiene cookies de sesión en `httpx.Cookies`, espera 1.5–4 s y nunca aborta ante 403/429/captcha: pinta `[Fallido/Bloqueado]` y sigue. Cada nodo se flushea a `logs/results.json`. `main.py` acepta modo interactivo o `python main.py <objetivo> -d <n>`.
- **Errores detectados/pendientes:** Instagram, Facebook, TikTok y X suelen bloquear clientes anónimos (403/captcha); el motor lo registra y continúa. No hay bypass de Cloudflare. El parseo de usernames ya está verificado en local; no se lanzó un crawl real (implica red + retardos de varios segundos por plataforma).
- **Siguientes pasos recomendados:** `pip install -r requirements.txt` y `python main.py dipargu -d 1`. Siguiente mejora útil: flag `--platforms github,reddit` y/o GitHub REST para confirmaciones más limpias.

_Actualizado: 2026-10-20T15:25:00+00:00_
