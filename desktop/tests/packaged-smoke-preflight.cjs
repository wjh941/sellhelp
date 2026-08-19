function registeredSellHelpInstallations(serializedRegistrations) {
  if (!serializedRegistrations.trim()) {
    return []
  }
  const registrations = JSON.parse(serializedRegistrations)
  const entries = Array.isArray(registrations) ? registrations : [registrations]
  return entries
    .filter((entry) => /^sellhelp(?:\s+\d+\.\d+\.\d+(?:[-+][0-9a-z.-]+)?)?$/i.test(entry?.DisplayName?.trim() || ''))
    .map((entry) => entry.InstallLocation?.trim() || '<unknown installation directory>')
}

module.exports = {
  registeredSellHelpInstallations,
}
