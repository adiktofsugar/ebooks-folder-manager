export interface DrmAction {
  type: 'drm';
}
export interface RenameAction {
  type: 'rename';
}
export interface PrintAction {
  type: 'print';
  filename?: string;
}
export type Action = DrmAction | RenameAction | PrintAction;