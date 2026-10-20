# SpiderNet V2 — Context Log

- **Última acción realizada:** Rotación de cabeceras reales de navegador, catálogo ampliado a 34 plataformas y rate-limit 0.5–2 s entre dominios distintos.
- **Cómo se ha implementado:** `core/spider.py` elige al azar uno de 10 perfiles (Chrome/Firefox/Safari/Edge, escritorio y móvil) por petición, con `Accept-Language`, `Accept-Encoding`, `Sec-Fetch-*` y `sec-ch-ua` cuando aplica. GitHub ya no se golpea en HTML: se consulta `https://api.github.com/users/{username}` (Accept `application/vnd.github+json`). GitLab y Reddit usan endpoints JSON públicos. El catálogo en `modules/platform_check.py` incluye Twitch, Pinterest, Spotify, Steam, Vimeo, Medium, Patreon, GitLab, Blogger, Telegram, LinkedIn, Tumblr, SoundCloud, etc. Entre hosts distintos hay `sleep` 0.5–2 s; en el mismo host, 0.25–0.8 s.
- **Errores detectados/pendientes:** GitHub queda verificado (octocat → 200, usuario inexistente → 404). Instagram, Facebook, TikTok, X y LinkedIn pueden seguir devolviendo 403/captcha a clientes anónimos; se marcan como bloqueados sin tumbar el crawl.
- **Siguientes pasos recomendados:** Lanzar `python main.py dipargu -d 0` para el barrido completo (~34 peticiones, ~20–60 s). Si se quiere acortar, añadir `--platforms github,gitlab,reddit,telegram`.

_Actualizado: 2026-10-20T15:45:00+00:00_
