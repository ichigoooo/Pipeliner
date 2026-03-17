type ReasonTranslator = ((key: string, values?: Record<string, string | number>) => string) & {
  has?: (key: string) => boolean;
};

function hasKey(t: ReasonTranslator, key: string): boolean {
  return typeof t.has === 'function' ? t.has(key) : true;
}

export function formatRunStopReason(
  reason: string | null | undefined,
  t: ReasonTranslator
): string | null {
  if (!reason) {
    return null;
  }

  const normalized = reason.trim();

  if (normalized === 'manual_stop' && hasKey(t, 'stopReasons.manualStop')) {
    return t('stopReasons.manualStop');
  }
  if (normalized === 'no_dispatchable_nodes' && hasKey(t, 'stopReasons.noDispatchableNodes')) {
    return t('stopReasons.noDispatchableNodes');
  }
  if (normalized === 'terminal_state' && hasKey(t, 'stopReasons.terminalState')) {
    return t('stopReasons.terminalState');
  }
  if (normalized === 'max_steps_exceeded' && hasKey(t, 'stopReasons.maxStepsExceeded')) {
    return t('stopReasons.maxStepsExceeded');
  }
  if (normalized === 'timeout guard exceeded' && hasKey(t, 'stopReasons.timeoutGuardExceeded')) {
    return t('stopReasons.timeoutGuardExceeded');
  }
  if (normalized === 'exceeded max_rework_rounds' && hasKey(t, 'stopReasons.reworkLimit')) {
    return t('stopReasons.reworkLimit');
  }
  if (normalized === 'validator blocked' && hasKey(t, 'stopReasons.validatorBlocked')) {
    return t('stopReasons.validatorBlocked');
  }
  if (normalized === 'validator requested revise' && hasKey(t, 'stopReasons.validatorRequestedRevise')) {
    return t('stopReasons.validatorRequestedRevise');
  }
  if (normalized === 'executor timeout' && hasKey(t, 'stopReasons.executorTimeout')) {
    return t('stopReasons.executorTimeout');
  }
  if (normalized === 'validator timeout' && hasKey(t, 'stopReasons.validatorTimeout')) {
    return t('stopReasons.validatorTimeout');
  }
  if (normalized === 'executor first byte timeout' && hasKey(t, 'stopReasons.executorFirstByteTimeout')) {
    return t('stopReasons.executorFirstByteTimeout');
  }
  if (normalized === 'validator first byte timeout' && hasKey(t, 'stopReasons.validatorFirstByteTimeout')) {
    return t('stopReasons.validatorFirstByteTimeout');
  }
  if (normalized === 'executor failed' && hasKey(t, 'stopReasons.executorFailed')) {
    return t('stopReasons.executorFailed');
  }
  if (normalized === 'validator failed' && hasKey(t, 'stopReasons.validatorFailed')) {
    return t('stopReasons.validatorFailed');
  }
  if (
    normalized === 'claude process exited unexpectedly' &&
    hasKey(t, 'stopReasons.claudeProcessExited')
  ) {
    return t('stopReasons.claudeProcessExited');
  }
  if (
    normalized === 'claude call metadata became stale before completion' &&
    hasKey(t, 'stopReasons.claudeCallStale')
  ) {
    return t('stopReasons.claudeCallStale');
  }
  if (
    normalized === 'driver failed: stale auto-drive recovered from archived callbacks' &&
    hasKey(t, 'stopReasons.driverStaleRecovered')
  ) {
    return t('stopReasons.driverStaleRecovered');
  }
  if (normalized.startsWith('driver failed:') && hasKey(t, 'stopReasons.driverFailed')) {
    const detail = normalized.slice('driver failed:'.length).trim();
    return t('stopReasons.driverFailed', { detail: detail || '-' });
  }
  if (normalized.startsWith('executor command failed') && hasKey(t, 'stopReasons.executorCommandFailed')) {
    return t('stopReasons.executorCommandFailed');
  }
  if (normalized.startsWith('validator command failed') && hasKey(t, 'stopReasons.validatorCommandFailed')) {
    return t('stopReasons.validatorCommandFailed');
  }
  if (normalized.startsWith('run 状态异常:') && hasKey(t, 'stopReasons.runStateUnexpected')) {
    return t('stopReasons.runStateUnexpected', { detail: normalized.replace('run 状态异常:', '').trim() || '-' });
  }

  if (hasKey(t, 'stopReasons.unknown')) {
    return t('stopReasons.unknown', { detail: normalized });
  }
  return normalized;
}
