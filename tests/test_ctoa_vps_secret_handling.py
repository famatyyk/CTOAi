from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CTOA_VPS = ROOT / "scripts" / "ops" / "ctoa-vps.ps1"


def read_ctoa_vps() -> str:
    return CTOA_VPS.read_text(encoding="utf-8")


def test_write_github_pat_does_not_embed_secret_in_remote_command() -> None:
    text = read_ctoa_vps()

    assert "echo GITHUB_PAT=$pat" not in text
    assert "GITHUB_PAT=$pat" not in text
    assert "sed -i '/^GITHUB_PAT/d' /opt/ctoa/.env" not in text
    assert 'Invoke-SshCommand "sed -i' not in text


def test_write_github_pat_validates_token_shape_before_transfer() -> None:
    text = read_ctoa_vps()

    assert "function Assert-GithubPatValue" in text
    assert "CTOA_GITHUB_PAT must not be empty." in text
    assert "CTOA_GITHUB_PAT must not contain newlines." in text
    assert "CTOA_GITHUB_PAT contains unsupported characters." in text
    assert "^[A-Za-z0-9_]{20,512}$" in text
    assert "$safePat = Assert-GithubPatValue $Pat" in text


def test_write_github_pat_uses_temp_file_copy_and_remote_cleanup() -> None:
    text = read_ctoa_vps()

    assert "ctoa-github-pat-{0}.env" in text
    assert "/tmp/ctoa-github-pat-$([Guid]::NewGuid().ToString('N')).env" in text
    assert 'Set-Content -LiteralPath $localTmp -Value ("GITHUB_PAT={0}" -f $safePat)' in text
    assert "Invoke-WithSshRetry -Label 'CopyGithubPat'" in text
    assert "& scp" in text
    assert "remote_pat_file='$remoteTmp'" in text
    assert "grep -v '^GITHUB_PAT=' /opt/ctoa/.env" in text
    assert 'cat "`$remote_pat_file" >> "`$tmp"' in text
    assert 'install -m 600 "`$tmp" /opt/ctoa/.env' in text
    assert 'rm -f "`$tmp" "`$remote_pat_file"' in text
    assert "Remove-Item -LiteralPath $localTmp -Force" in text


def test_write_github_pat_action_uses_secret_safe_helper() -> None:
    text = read_ctoa_vps()

    assert "'WriteGithubPat' {" in text
    assert "Write-RemoteGithubPat $pat" in text


def test_ensure_gs_env_keys_does_not_embed_secrets_in_remote_script() -> None:
    text = read_ctoa_vps()

    assert "__OPENAI_KEY__" not in text
    assert "__GITHUB_PAT__" not in text
    assert "$safeOpenAi = $openAiKey -replace" not in text
    assert "$safeGithubPat = $githubPat -replace" not in text
    assert "upsert_if_missing_or_empty OPENAI_API_KEY '__OPENAI_KEY__'" not in text
    assert "function Assert-EnvSecretValue" in text
    assert "function Write-RemoteGsEnvKeys" in text
    assert "Write-RemoteGsEnvKeys $openAiKey $githubPat" in text


def test_ensure_gs_env_keys_uses_temp_file_copy_and_remote_cleanup() -> None:
    text = read_ctoa_vps()

    assert "ctoa-gs-env-{0}.env" in text
    assert "/tmp/ctoa-gs-env-$([Guid]::NewGuid().ToString('N')).env" in text
    assert 'Set-Content -LiteralPath $localTmp -Value $lines -Encoding ASCII' in text
    assert "Invoke-WithSshRetry -Label 'CopyGsEnvKeys'" in text
    assert "remote_env_file='$remoteTmp'" in text
    assert "OPENAI_API_KEY|GITHUB_PAT" in text
    assert 'done < "`$remote_env_file"' in text
    assert 'rm -f "`$remote_env_file"' in text
    assert "Remove-Item -LiteralPath $localTmp -Force" in text


def test_vps_remote_target_env_is_validated_before_ssh_or_scp() -> None:
    text = read_ctoa_vps()

    assert "function Assert-VpsUser" in text
    assert "function Assert-VpsHost" in text
    assert "CTOA_VPS_USER contains unsupported characters." in text
    assert "CTOA_VPS_HOST contains unsupported characters." in text
    assert "CTOA_VPS_USER must not contain leading or trailing whitespace." in text
    assert "CTOA_VPS_HOST must not contain leading or trailing whitespace." in text
    assert "$user -cnotmatch '^[a-z_][a-z0-9_-]{0,31}$'" in text
    assert "^[a-z_][a-z0-9_-]{0,31}$" in text
    assert "CTOA_VPS_HOST is too long." in text
    assert "CTOA_VPS_HOST contains an invalid DNS label." in text
    assert "CTOA_VPS_HOST must use bracketed IPv6 syntax." in text
    assert "^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$" in text
    assert "$h = Assert-VpsHost $h" in text
    assert "$u = Assert-VpsUser $u" in text


def test_vps_key_path_is_resolved_literal_file() -> None:
    text = read_ctoa_vps()

    assert "Test-Path -LiteralPath $k -PathType Leaf" in text
    assert "Resolve-Path -LiteralPath $k" in text


def test_root_wrapper_copy_uses_random_remote_temp_and_cleanup() -> None:
    text = read_ctoa_vps()

    assert "$remoteTmp = '/tmp/ctoa-root-action.sh'" not in text
    assert "/tmp/ctoa-root-action-$([Guid]::NewGuid().ToString('N')).sh" in text
    assert "Invoke-WithSshRetry -Label 'CopyRootWrapper'" in text
    assert "trap 'rm -f $remoteTmp' EXIT" in text
    assert "sudo -n /usr/bin/install -m 750 $remoteTmp $remoteDst" in text


def test_vps_operator_inputs_use_shared_remote_validation_helpers() -> None:
    text = read_ctoa_vps()

    assert "function Assert-CtoaServerUrl" in text
    assert "function Resolve-CtoaServerUrlList" in text
    assert "function ConvertTo-RemoteSqlLiteral" in text
    assert "function Assert-CtoaServiceName" in text
    assert "function Assert-CtoaGitRef" in text
    assert "function Assert-CtoaUtcTime" in text
    assert "function Assert-CtoaIntegerRange" in text
    assert "contains unsupported remote-script characters" in text


def test_invalid_server_url_warning_does_not_echo_rejected_value() -> None:
    text = read_ctoa_vps()

    assert "Invalid server URL ignored; using fallback." in text
    assert "Invalid server URL ignored; using fallback: $u" not in text
    assert 'Write-Warning "Invalid server URL ignored' not in text


def test_vps_sql_url_service_and_ref_inputs_do_not_use_ad_hoc_quoting() -> None:
    text = read_ctoa_vps()

    assert '$safeFilterUrl = $filterUrl -replace' not in text
    assert '$safeFilterStatus = $filterStatus.ToUpperInvariant() -replace' not in text
    assert '$safeUrl = $watchUrl -replace' not in text
    assert '$safeUrl = $serverUrl -replace' not in text
    assert '$safeName = $serverName -replace' not in text
    assert '$safeUrl = $url -replace' not in text
    assert '$safeRef = $sourceRef -replace' not in text
    assert "ConvertTo-RemoteSqlLiteral 'CTOA_FILTER_URL'" in text
    assert "ConvertTo-RemoteSqlLiteral 'CTOA_WATCH_URL'" in text
    assert "ConvertTo-RemoteSqlLiteral 'CTOA_SERVER_URL'" in text
    assert "ConvertTo-RemoteSqlLiteral 'CTOA_SERVER_URLS'" in text
    assert "Assert-CtoaServiceName $svc" in text
    assert "Assert-CtoaGitRef $sourceRef -AllowEmpty" in text
    assert "Assert-CtoaGitRef $sourceRef" in text


def test_vps_reseed_and_mythibia_inputs_are_validated_before_remote_placeholders() -> None:
    text = read_ctoa_vps()

    assert "Resolve-CtoaServerUrlList (Get-OptionalEnv 'CTOA_RESEED_TIER_AB_URLS'" in text
    assert "Resolve-CtoaServerUrlList (Get-OptionalEnv 'CTOA_RESEED_TIER_C_URLS'" in text
    assert "Assert-CtoaIntegerRange 'CTOA_RESEED_AB_INTERVAL_MINUTES'" in text
    assert "Assert-CtoaIntegerRange 'CTOA_RESEED_ERROR_MIN_AGE_HOURS_AB'" in text
    assert "Assert-CtoaIntegerRange 'CTOA_RESEED_ERROR_MIN_AGE_HOURS_C'" in text
    assert "Assert-CtoaIntegerRange 'CTOA_RESEED_ERROR_MIN_AGE_HOURS'" in text
    assert "Assert-CtoaUtcTime (Get-OptionalEnv 'CTOA_RESEED_C_DAILY_UTC'" in text
    assert "URL=$safeUrl" in text
    assert "URL='$safeUrl'" not in text


def test_generated_reseed_tier_script_validates_runtime_env_values() -> None:
    text = read_ctoa_vps()

    assert "is_safe_reseed_url() {" in text
    assert "is_safe_reseed_hours() {" in text
    assert "sql_literal() {" in text
    assert "http://*|https://*) ;;" in text
    assert '[ "${#candidate}" -le 2048 ] || return 1' in text
    assert 'if ! is_safe_reseed_hours "$ERROR_MIN_AGE_HOURS"; then' in text
    assert 'if ! is_safe_reseed_url "$url"; then' in text
    assert 'echo "[reseed-tier][$TIER] skip unsafe url: $url"' in text
    assert 'url_literal="$(sql_literal "$url")"' in text
    assert "WHERE url='$url'" not in text
    assert "WHERE url=${url_literal}" in text


def test_generated_reseed_installer_uses_private_env_temp_file() -> None:
    text = read_ctoa_vps()

    assert "/opt/ctoa/.env.tmp" not in text
    assert "update_env_key() {" in text
    assert 'tmp="$(mktemp /opt/ctoa/.env.XXXXXX)"' in text
    assert 'grep -v "^${key}=" /opt/ctoa/.env > "$tmp" || true' in text
    assert 'install -m 600 "$tmp" /opt/ctoa/.env' in text
    assert "update_env_key 'CTOA_RESEED_TIER_AB_URLS' '__TIER_AB_URLS__'" in text
    assert "update_env_key 'CTOA_RESEED_ERROR_MIN_AGE_HOURS' '__ERROR_MIN_AGE_HOURS__'" in text
