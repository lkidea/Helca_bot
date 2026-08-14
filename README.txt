SL spojuje do jednoho stringu, ale zachovává mezery
L kontroluje slova jedno po druhém samostatně jako celky
L i SL vynechává interpunkci a emoji, S ani jedno

R je reply, M je jen prostá message 


xwcx je wildcard za 1 nebo 0 slov... lze jich v jednom triggeru použít víc
funguje u všech typů, u L i s tím porovnáváním po jednom slovu, ale ještě jsem to důkladně nezkoušel, zda nejsou bugy
{
    "trigger_type": "SL",
    "trigger": "nenechávejte ho xwcx",
    "response_type": "R",
    "response": "grrrrr"
  },
se nespustí, pokud je zpráva jen nenechávej ho, což je ale koneckonců správně, kdyby mi bylo jedno, jestli tam něco je nebo ne, nedával bych tam wildcard 


triggery mohou být v listu pro stejné odpovědi,
odpovědi mohou být v listu pro stejné tagy






https://dashboard.render.com/web/srv-d9iimcjtqb8s738uvbh0        třeba updatovat ručně 
