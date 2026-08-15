# ⚠️ Este proyecto se movió

El mapa de ayuda del sismo vive ahora en su propio repositorio:

    https://github.com/reruizc/ayuda-sismo
    ~/ayuda-sismo   (copia de trabajo local)

Salió del monorepo para que se pueda colaborar sin clonar 2,8 GB de historia
ajena y para poder entregárselo con licencia a las organizaciones que lo
mantengan. La historia de la carpeta se preservó con `git subtree split`.

Esta copia queda CONGELADA. No editar acá: los cambios no llegan al repo nuevo
ni a producción.

Se elimina cuando la conversación que está trabajando en el Worker
(`worker/src/index.js`, `inteligencia.js`) termine y confirme, con:

    git rm -r ayuda-sismo tools/ayuda-sismo
