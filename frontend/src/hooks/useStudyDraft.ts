import { useCallback, useEffect, useState, type SetStateAction } from "react";
import type { z } from "zod";

import { useAuth } from "../app/authContext";

// Keeps a study form's entries for the life of the browser tab, so a reload, Back or a trip
// through the sidebar does not throw away a half-filled form.
//
// The draft lives in sessionStorage, never localStorage: it is gone when the tab closes, so
// nothing typed on a shared computer waits there for the next person. The key carries the
// user id, so one user never sees another user's entries. A stored draft is used only when it
// still matches the form's schema; anything unreadable is dropped without a word. Every
// storage access is guarded - a private window may refuse it, and the form must keep working
// in memory then.

const DRAFT_KEY_PREFIX = "keos:draft:v1:";

function userPrefix(userId: string): string {
  return `${DRAFT_KEY_PREFIX}${userId}:`;
}

function draftKey(userId: string, module: string): string {
  return `${userPrefix(userId)}${module}`;
}

function removeKey(key: string): void {
  try {
    window.sessionStorage.removeItem(key);
  } catch {
    // Nothing to do: there is no other place the draft could be stored.
  }
}

function readDraft<T>(key: string, schema: z.ZodType<T>): T | null {
  try {
    const stored = window.sessionStorage.getItem(key);
    if (stored === null) {
      return null;
    }
    const checked = schema.safeParse(JSON.parse(stored));
    if (checked.success) {
      return checked.data;
    }
  } catch {
    // Unreadable: treated like a draft of an older shape below.
  }
  removeKey(key);
  return null;
}

function writeDraft(key: string, draft: unknown): void {
  try {
    window.sessionStorage.setItem(key, JSON.stringify(draft));
  } catch {
    // Storage full or refused: the entries still hold for this page, only not across a reload.
  }
}

/** Remove every stored draft of one user (on a deliberate sign-out). */
export function clearStudyDrafts(userId: string): void {
  const prefix = userPrefix(userId);
  try {
    const keys: string[] = [];
    for (let index = 0; index < window.sessionStorage.length; index += 1) {
      const key = window.sessionStorage.key(index);
      if (key !== null && key.startsWith(prefix)) {
        keys.push(key);
      }
    }
    keys.forEach(removeKey);
  } catch {
    // Storage refused: then nothing was stored either.
  }
}

export type StudyDraftOptions<T> = {
  /** Short, stable module name, part of the storage key (e.g. "transformer"). */
  module: string;
  /** A fresh empty draft; called on first use, after an unusable restore and on clear. */
  createInitial: () => T;
  /** The shape a stored draft must still have to be restored. */
  schema: z.ZodType<T>;
};

export type StudyDraft<T> = {
  draft: T;
  setDraft: (next: SetStateAction<T>) => void;
  /** True when the entries on screen came back from this tab's storage and are not edited yet. */
  restored: boolean;
  /** Forget the stored draft and start again from an empty form. */
  clear: () => void;
};

type DraftState<T> = {
  key: string | null;
  draft: T;
  restored: boolean;
  /** Only a draft the user has changed is written; an untouched empty form is not stored. */
  edited: boolean;
};

function load<T>(key: string | null, options: StudyDraftOptions<T>): DraftState<T> {
  const stored = key === null ? null : readDraft(key, options.schema);
  return stored === null
    ? { key, draft: options.createInitial(), restored: false, edited: false }
    : { key, draft: stored, restored: true, edited: false };
}

export function useStudyDraft<T>(options: StudyDraftOptions<T>): StudyDraft<T> {
  const { state: authState } = useAuth();
  const userId = authState.status === "signed-in" ? authState.session.user.id : null;
  // Not signed in: plain state in memory, nothing is written.
  const key = userId === null ? null : draftKey(userId, options.module);

  const [state, setState] = useState<DraftState<T>>(() => load(key, options));

  // Another user (or none) now: that user's own draft, never the previous one's.
  if (state.key !== key) {
    setState(load(key, options));
  }

  useEffect(() => {
    if (state.key !== null && state.edited) {
      writeDraft(state.key, state.draft);
    }
  }, [state]);

  const setDraft = useCallback((next: SetStateAction<T>) => {
    setState((current) => ({
      ...current,
      draft: typeof next === "function" ? (next as (previous: T) => T)(current.draft) : next,
      // The restore notice only says the form came back; after an edit it is noise.
      restored: false,
      edited: true,
    }));
  }, []);

  const { createInitial } = options;
  const clear = useCallback(() => {
    if (key !== null) {
      removeKey(key);
    }
    setState({ key, draft: createInitial(), restored: false, edited: false });
  }, [key, createInitial]);

  return { draft: state.draft, setDraft, restored: state.restored, clear };
}
