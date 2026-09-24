// Artifact IDs are opaque; the most recently created trusted checkpoint wins.
function orderCheckpoints(artifacts, branch) {
  const candidates = artifacts.filter(a => a.workflow_run?.head_branch === branch);
  if (candidates.some(a => !Number.isFinite(Date.parse(a.created_at)))) {
    throw new Error('Invalid checkpoint creation timestamp');
  }
  return candidates.sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at) || b.id - a.id);
}
module.exports = {orderCheckpoints};
