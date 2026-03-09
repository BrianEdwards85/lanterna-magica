(ns lanterna-magica.components.current-status
  "Make Current / Deactivate button pair for revision and configuration items."
  (:require
   [lanterna-magica.bp :as bp]))

;; ---------------------------------------------------------------------------
;; Current Status Controls
;; ---------------------------------------------------------------------------

(defn current-status-controls
  "Renders a Make Current or Deactivate button depending on `is-current?`.
   Stops event propagation before invoking the callback, so callers receive
   a zero-argument callback.
   Props: {:keys [is-current? on-make-current on-deactivate]}"
  [{:keys [is-current? on-make-current on-deactivate]}]
  (if is-current?
    [bp/button {:text "Deactivate" :minimal true :small true
                :intent "danger"
                :on-click (fn [e] (.stopPropagation e) (on-deactivate))}]
    [bp/button {:text "Make Current" :minimal true :small true
                :intent "success"
                :on-click (fn [e] (.stopPropagation e) (on-make-current))}]))
