# Created by Harsh (@harsh-91) | Made in India
$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $projectRoot '.env'
$settings = @{}
Get-Content -LiteralPath $envFile | ForEach-Object {
    if ($_ -match '^([^#=]+)=(.*)$') {
        $settings[$matches[1]] = $matches[2]
    }
}

$postgresBin = 'C:\Program Files\PostgreSQL\17\bin'
$psql = Join-Path $postgresBin 'psql.exe'
$createdb = Join-Path $postgresBin 'createdb.exe'
$dbName = $settings['POSTGRES_DB']
$dbUser = $settings['POSTGRES_USER']
$dbPassword = $settings['POSTGRES_PASSWORD']
$dbPort = $settings['POSTGRES_PORT']
$dbHost = '127.0.0.1'
$schema = Join-Path $projectRoot 'init\01-schema.sql'
$csv = (Join-Path $projectRoot 'init\transactions.csv').Replace('\', '/')

if (-not (Test-Path -LiteralPath $psql)) {
    throw "PostgreSQL client was not found at $psql"
}

$env:PGPASSWORD = $dbPassword
try {
    $roleExists = & $psql -h $dbHost -p $dbPort -U postgres -d postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname = '$dbUser'"
    if ($roleExists -ne '1') {
        & $psql -h $dbHost -p $dbPort -U postgres -d postgres -v ON_ERROR_STOP=1 -c "CREATE ROLE $dbUser LOGIN PASSWORD '$dbPassword';"
    }

    $databaseExists = & $psql -h $dbHost -p $dbPort -U postgres -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '$dbName'"
    if ($databaseExists -ne '1') {
        & $createdb -h $dbHost -p $dbPort -U postgres -O $dbUser $dbName
    }

    & $psql -h $dbHost -p $dbPort -U $dbUser -d $dbName -v ON_ERROR_STOP=1 -f $schema
    $rowCount = [int](& $psql -h $dbHost -p $dbPort -U $dbUser -d $dbName -tAc 'SELECT COUNT(*) FROM bank_transactions')
    if ($rowCount -eq 0) {
        $copy = "\copy bank_transactions (account_number, statement_date, statement_period_start, statement_period_end, source_file, source_row, transaction_date, details, reference_number, debit, credit, balance, statement_metadata) FROM '$csv' WITH (FORMAT csv, HEADER true, NULL '');"
        & $psql -h $dbHost -p $dbPort -U $dbUser -d $dbName -v ON_ERROR_STOP=1 -c $copy
    }
} finally {
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
}
