# Tennis Court Booking Automation

Script automatisé pour réserver des courts de tennis à Southwark Park via GitHub Actions.

## Configuration

### 1. Secrets GitHub requis

Allez dans Settings > Secrets and variables > Actions et ajoutez :

- `TENNIS_USERNAME` : Votre nom d'utilisateur
- `TENNIS_PASSWORD` : Votre mot de passe
- `CARD_NUMBER` : Numéro de carte (optionnel)
- `CARD_EXPIRY` : Date d'expiration MM/YY (optionnel)
- `CARD_CVC` : Code CVC (optionnel)

### 2. Utilisation

#### Via l'interface GitHub :
1. Allez dans l'onglet "Actions"
2. Cliquez sur "Book Tennis Court"
3. Cliquez sur "Run workflow"
4. Entrez la date et l'heure
5. Cliquez sur "Run workflow"

#### Via l'API :
```bash
curl -X POST \
  -H "Authorization: token YOUR_GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/YOUR_USERNAME/tennis-booking/actions/workflows/book-tennis.yml/dispatches \
  -d '{"ref":"main","inputs":{"date":"2025-06-16","hour":"7"}}'
```

## Logs

Les logs et captures d'écran sont disponibles dans les artifacts de chaque run.

## Support

Pour toute question, créez une issue dans ce repository.