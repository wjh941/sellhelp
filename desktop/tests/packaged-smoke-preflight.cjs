function registeredSellHelpInstallations(serializedRegistrations) {
  if (!serializedRegistrations.trim()) {
    return []
  }
  const registrations = JSON.parse(serializedRegistrations)
  const entries = Array.isArray(registrations) ? registrations : [registrations]
  return entries
    .filter((entry) => entry?.DisplayName?.trim().toLowerCase() === 'sellhelp')
    .map((entry) => entry.InstallLocation?.trim() || '<unknown installation directory>')
}

module.exports = {
  registeredSellHelpInstallations,
}
