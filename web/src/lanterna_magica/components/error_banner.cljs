(ns lanterna-magica.components.error-banner
  "Error banner component."
  (:require
   [lanterna-magica.bp :as bp]))

;; ---------------------------------------------------------------------------
;; Error Banner
;; ---------------------------------------------------------------------------

(defn error-banner
  "Show an error callout. Pass either a string or a fallback string + GraphQL errors vector."
  ([message]
   (when message
     [bp/callout {:intent "danger" :class "mb-4" :icon "error"}
      message]))
  ([fallback errors]
   (let [detail (some-> errors first (get "message"))]
     [bp/callout {:intent "danger" :class "mb-4" :icon "error"}
      (if detail (str fallback " " detail) fallback)])))
