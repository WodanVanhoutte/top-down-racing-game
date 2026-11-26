# top-down-racing-game
Dit is een opdracht in het tweede jaar bachelor Elektronica-ICT afstudeerrichting Elektronica. We maken een spel waarbij een AI model zelf zal moeten leren racen en zo snel mogelijk circuits zal moeten afleggen.

## Spelen

Maak eerst een eigen virtuele Python-omgeving aan vanuit de hoofdmap van het project:

Verwijder een eventueel bestaande `.venv` eerst; virtuele omgevingen zijn niet verplaatsbaar.

```powershell
py -3 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Start daarna het spel:

```powershell
python .\10racegame\race_game\racegame_gp.py
```

Elke teamgenoot maakt zelf een `.venv` aan op zijn computer. Deze map is uitgesloten van Git omdat een virtuele omgeving verwijzingen naar de lokale Python-installatie bevat en niet tussen computers kan worden gedeeld.
