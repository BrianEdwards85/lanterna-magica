(ns lanterna-magica.events.helpers
  "Helpers to reduce loading/error boilerplate in event handlers.")

(defn start-loading
  "Mark a loading key as active and clear its error."
  [db key]
  (-> db
      (update :loading conj key)
      (assoc-in [:errors key] nil)))

(defn stop-loading
  "Remove a loading key and optionally set its error."
  ([db key]
   (update db :loading disj key))
  ([db key errors]
   (-> db
       (update :loading disj key)
       (assoc-in [:errors key] errors))))
