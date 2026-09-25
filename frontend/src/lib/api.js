import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const createRun = (payload) => axios.post(`${API}/runs`, payload).then((r) => r.data);
export const getRun = (runId) => axios.get(`${API}/runs/${runId}`).then((r) => r.data);
export const finalizeRun = (runId) => axios.post(`${API}/runs/${runId}/finalize`).then((r) => r.data);
export const updateHappyPath = (runId, happyPath) =>
  axios.put(`${API}/runs/${runId}/happy-path`, { happy_path: happyPath }).then((r) => r.data);
export const generateWireframes = (runId) => axios.post(`${API}/runs/${runId}/generate-wireframes`).then((r) => r.data);
export const submitFeedback = (runId, { instruction, scope, screenName, file, elementContext }) => {
  const form = new FormData();
  form.append("instruction", instruction);
  form.append("scope", scope);
  if (screenName) form.append("screen_name", screenName);
  if (file) form.append("file", file);
  if (elementContext) form.append("element_context", elementContext);
  return axios.post(`${API}/runs/${runId}/feedback`, form, { headers: { "Content-Type": "multipart/form-data" } }).then((r) => r.data);
};
export const uploadSrsFile = (file) => {
  const form = new FormData();
  form.append("file", file);
  return axios.post(`${API}/upload-srs`, form, { headers: { "Content-Type": "multipart/form-data" } }).then((r) => r.data);
};
export const downloadRunUrl = (runId) => `${API}/runs/${runId}/download`;
export const allWireframesPreviewUrl = (runId) => `${API}/runs/${runId}/preview-all`;

export const getAgents = () => axios.get(`${API}/agents`).then((r) => r.data);
export const createAgent = (payload) => axios.post(`${API}/agents`, payload).then((r) => r.data);
export const updateAgent = (id, payload) => axios.put(`${API}/agents/${id}`, payload).then((r) => r.data);
export const deleteAgent = (id) => axios.delete(`${API}/agents/${id}`).then((r) => r.data);
export const getActiveFlow = () => axios.get(`${API}/flows/active`).then((r) => r.data);
export const updateActiveFlow = (payload) => axios.put(`${API}/flows/active`, payload).then((r) => r.data);
export const getLlmSettings = () => axios.get(`${API}/settings/llm`).then((r) => r.data);
export const updateLlmSettings = (payload) => axios.put(`${API}/settings/llm`, payload).then((r) => r.data);
export const updateEyIncubatorConfig = (payload) => axios.put(`${API}/settings/llm/ey-incubator`, payload).then((r) => r.data);
export const updateLlmApiKey = (provider, apiKey) => axios.put(`${API}/settings/llm/keys`, { provider, api_key: apiKey }).then((r) => r.data);
export const deleteLlmApiKey = (provider) => axios.delete(`${API}/settings/llm/keys/${provider}`).then((r) => r.data);
export const getModelChoices = () => axios.get(`${API}/model-choices`).then((r) => r.data);
