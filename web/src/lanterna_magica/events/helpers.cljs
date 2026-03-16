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

(defn base-dimension-ids
  "Return a vector of IDs for the base dimension of each type,
  scanning all entries in [:all-dimensions] in db."
  [db]
  (->> (vals (:all-dimensions db))
       (apply concat)
       (filter #(true? (:base %)))
       (mapv :id)))

(defn find-type-id
  "Return the type ID for dimension-id by scanning [:all-dimensions] in db,
  or nil if the dimension is not found."
  [db dimension-id]
  (some (fn [dim]
          (when (= (:id dim) dimension-id)
            (get-in dim [:type :id])))
        (apply concat (vals (:all-dimensions db)))))
